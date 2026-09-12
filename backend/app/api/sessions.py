"""Sessions API router."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.agents.orchestrator import GroundedConversationalAgent
from app.db.database import get_db
from app.llm import LLMError
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.session import SessionResponse, SessionWithMessagesResponse
from app.services.session import SessionNotFoundError, SessionService

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
