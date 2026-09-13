"""Sessions API router."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.agents.orchestrator import GroundedConversationalAgent
from app.db.database import get_db
from app.llm import LLMError
from app.schemas.essay import EssayCreate, EssayResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.session import SessionResponse, SessionWithMessagesResponse
from app.services.session import SessionNotFoundError, SessionService
from app.skills.ship30 import Ship30Skill

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

    # 2. Load bounded recent history (excludes the message we just added
    # since we pass the latest question explicitly to the agent, although
    # the orchestrator signature accepts question + history, so we'll just
    # fetch history *before* this turn)
    # Actually, SessionService.get_recent_history will include the user message
    # we just saved! So let's pass it to the agent, but the orchestrator expects
    # question explicitly. Let's adjust logic:
    
    # We will pass the full history EXCEPT the latest user message to history,
    # or just let Orchestrator build the messages list differently.
    # The simplest is to fetch history BEFORE adding the user message.
    
    # Let's rollback that thought — we already added it. 
    # Let's fetch history. The last item is the user message.
    full_history = service.get_recent_history(session_id)
    # Extract the last message (the one we just added) as the question
    if full_history and full_history[-1]["role"] == "user":
        history = full_history[:-1]
    else:
        history = full_history

    # 3. Run the Agent
    agent = GroundedConversationalAgent(db)
    try:
        result = agent.answer_question(
            question=payload.content,
            history=history,
        )
    except LLMError as exc:
        logger.error("LLM Error during message processing: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in agent loop")
        raise HTTPException(status_code=500, detail="Internal server error")

    # 4. Save assistant response
    assistant_msg = service.add_assistant_message(
        session_id=session_id,
        content=result["answer"],
        citations=result["citations"],
        grounded=result["grounded"],
        provider=result["provider"],
    )

    return assistant_msg


@router.post("/{session_id}/essay", response_model=EssayResponse)
def create_essay(
    session_id: uuid.UUID,
    payload: EssayCreate,
    db=Depends(get_db),
) -> Any:
    """Generate a grounded Ship 30 for 30 essay from Lenny knowledge.

    This endpoint:
    1. Validates the session exists.
    2. Saves the user essay request as a message.
    3. Resolves the topic using the request + last 4 session messages.
    4. Retrieves grounding evidence from the knowledge base.
    5. Runs the Ship30Skill (up to 2 generation attempts with validation).
    6. Persists and returns the essay as an assistant message.
    """
    service = SessionService(db)

    # 1. Validate session
    try:
        service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Save user essay request as a message
    service.add_user_message(session_id, payload.content)

    # 3. Load bounded recent history for context resolution
    #    (last 4 messages, which includes the user message we just saved)
    from app.skills.ship30 import CONVERSATION_CONTEXT_LIMIT
    full_history = service.get_recent_history(session_id)
    # Exclude the just-added user message from context (it IS the request)
    if full_history and full_history[-1]["role"] == "user":
        context_history = full_history[:-1]
    else:
        context_history = full_history
    # Bound to CONVERSATION_CONTEXT_LIMIT
    bounded_history = context_history[-CONVERSATION_CONTEXT_LIMIT:]

    # 4. Run Ship30 skill
    skill = Ship30Skill(db)
    try:
        result = skill.run(
            request=payload.content,
            recent_history=bounded_history,
        )
    except LLMError as exc:
        logger.error("Ship30 LLM error session=%s: %s", session_id, exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in Ship30 skill session=%s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error")

    # 5. Persist essay as assistant message
    essay_msg = service.add_assistant_message(
        session_id=session_id,
        content=result.essay,
        citations=[c.model_dump(mode="json") for c in result.citations],
        grounded=result.grounded,
        provider=result.provider,
    )

    # 6. Build extended response with Ship30 metadata
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

    logger.info(
        "Ship30 essay complete session=%s provider=%r word_count=%d "
        "grounded=%r attempts=%d issues=%r",
        session_id,
        result.provider,
        result.word_count,
        result.grounded,
        result.generation_attempts,
        result.validation_issues,
    )

    return response_data
