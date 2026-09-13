"""Sessions API router."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.orchestrator import GroundedConversationalAgent
from app.db.database import get_db
from app.llm import LLMError
from app.schemas.artifact import ArtifactCreate, ArtifactResponse
from app.schemas.essay import EssayCreate, EssayResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.session import SessionResponse, SessionWithMessagesResponse
from app.services.session import SessionNotFoundError, SessionService
from app.services.artifact import ArtifactService
from app.skills.ship30 import Ship30Skill
from app.skills.artifact import ArtifactSkill
from app.logger import log_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(db=Depends(get_db)) -> Any:
    """Create a new conversational session."""
    service = SessionService(db)
    session = service.create_session()
    return session


@router.get("/{session_id}", response_model=SessionWithMessagesResponse)
def get_session(session_id: uuid.UUID, db=Depends(get_db)) -> Any:
    """Retrieve a session and its message history."""
    service = SessionService(db)
    try:
        session = service.get_session(session_id)
        return session
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/{session_id}/messages", response_model=MessageResponse)
def create_message(
    request: Request,
    session_id: uuid.UUID,
    payload: MessageCreate,
    db=Depends(get_db),
) -> Any:
    """Send a message to the assistant and get a grounded response.

    This triggers the full agentic tool-use loop:
    1. Saves the user message.
    2. Loads recent history.
    3. Runs the Orchestrator (which uses the Retriever tool).
    4. Saves and returns the assistant's grounded response with citations.
    """
    service = SessionService(db)

    # 1. Validate session and save user message
    try:
        service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    service.add_user_message(session_id, payload.content)
    
    log_event("message_received", request=request, session_id=str(session_id))

    full_history = service.get_recent_history(session_id)
    if full_history and full_history[-1]["role"] == "user":
        history = full_history[:-1]
    else:
        history = full_history

    # 3. Run the Agent
    agent = GroundedConversationalAgent(db)
    try:
        import time
        start = time.time()
        result = agent.answer_question(
            question=payload.content,
            history=history,
        )
        latency = int((time.time() - start) * 1000)
    except LLMError as exc:
        log_event("llm_error", request=request, session_id=str(session_id), level=logging.ERROR, error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        log_event("unexpected_error", request=request, session_id=str(session_id), level=logging.ERROR, error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")

    # 4. Save assistant response
    assistant_msg = service.add_assistant_message(
        session_id=session_id,
        content=result["answer"],
        citations=result["citations"],
        grounded=result["grounded"],
        provider=result["provider"],
    )

    log_event("message_completed", request=request, session_id=str(session_id), provider=result["provider"], latency_ms=latency, outcome="success" if result["grounded"] else "insufficient_context")

    return assistant_msg


@router.post("/{session_id}/essay", response_model=EssayResponse)
def create_essay(
    request: Request,
    session_id: uuid.UUID,
    payload: EssayCreate,
    db=Depends(get_db),
) -> Any:
    """Generate a grounded Ship 30 for 30 essay from Lenny knowledge."""
    service = SessionService(db)

    try:
        service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    service.add_user_message(session_id, payload.content)
    
    log_event("essay_requested", request=request, session_id=str(session_id))

    from app.skills.ship30 import CONVERSATION_CONTEXT_LIMIT
    full_history = service.get_recent_history(session_id)
    if full_history and full_history[-1]["role"] == "user":
        context_history = full_history[:-1]
    else:
        context_history = full_history
    bounded_history = context_history[-CONVERSATION_CONTEXT_LIMIT:]

    skill = Ship30Skill(db)
    try:
        import time
        start = time.time()
        result = skill.run(
            request=payload.content,
            recent_history=bounded_history,
        )
        latency = int((time.time() - start) * 1000)
    except LLMError as exc:
        log_event("ship30_llm_error", request=request, session_id=str(session_id), level=logging.ERROR, error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        log_event("ship30_unexpected_error", request=request, session_id=str(session_id), level=logging.ERROR, error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")

    essay_msg = service.add_assistant_message(
        session_id=session_id,
        content=result.essay,
        citations=[c.model_dump(mode="json") for c in result.citations],
        grounded=result.grounded,
        provider=result.provider,
    )

    response_data = EssayResponse(
        id=essay_msg.id,
        session_id=essay_msg.session_id,
        role=essay_msg.role,
        content=essay_msg.content,
        citations=essay_msg.citations,
        grounded=essay_msg.grounded,
        provider=essay_msg.provider,
        created_at=essay_msg.created_at,
        word_count=result.word_count,
        generation_attempts=result.generation_attempts,
        insufficient_evidence=result.insufficient_evidence,
        validation_issues=result.validation_issues,
    )

    log_event(
        "essay_completed",
        request=request,
        session_id=str(session_id),
        provider=result.provider,
        latency_ms=latency,
        word_count=result.word_count,
        grounded=result.grounded,
        attempts=result.generation_attempts,
        issues=result.validation_issues,
    )

    return response_data

@router.post("/{session_id}/artifacts", response_model=ArtifactResponse)
def create_artifact(
    request: Request,
    session_id: uuid.UUID,
    payload: ArtifactCreate,
    db=Depends(get_db),
) -> Any:
    """Generate and persist a new artifact."""
    service = SessionService(db)
    
    try:
        service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
        
    log_event("artifact_requested", request=request, session_id=str(session_id), type=payload.artifact_type)

    full_history = service.get_recent_history(session_id)
    
    skill = ArtifactSkill(db)
    try:
        import time
        start = time.time()
        result = skill.run(
            request=payload.request,
            artifact_type=payload.artifact_type,
            recent_history=full_history,
        )
        latency = int((time.time() - start) * 1000)
    except LLMError as exc:
        log_event("artifact_llm_error", request=request, session_id=str(session_id), level=logging.ERROR, error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        log_event("artifact_unexpected_error", request=request, session_id=str(session_id), level=logging.ERROR, error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")
        
    artifact_service = ArtifactService(db)
    artifact = artifact_service.create_artifact(
        session_id=session_id,
        artifact_type=result.artifact_type,
        content=result.content,
        request=payload.request,
        grounded=result.grounded,
        provider=result.provider,
        title=payload.request[:197] + "..." if len(payload.request) > 200 else payload.request,
    )
    
    log_event(
        "artifact_completed",
        request=request,
        session_id=str(session_id),
        provider=result.provider,
        latency_ms=latency,
        type=result.artifact_type,
        grounded=result.grounded,
    )
    
    return artifact


@router.get("/{session_id}/artifacts", response_model=list[ArtifactResponse])
def list_artifacts(
    session_id: uuid.UUID,
    db=Depends(get_db),
) -> Any:
    """List all artifacts for a session."""
    service = SessionService(db)
    try:
        service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
        
    artifact_service = ArtifactService(db)
    return artifact_service.list_artifacts(session_id)


@router.get("/{session_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    session_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db=Depends(get_db),
) -> Any:
    """Get a specific artifact."""
    artifact_service = ArtifactService(db)
    artifact = artifact_service.get_artifact(session_id, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact
