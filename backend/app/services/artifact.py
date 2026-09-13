"""Artifact service for persisting generated artifacts."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.artifact import Artifact
from app.services.session import SessionService


class ArtifactService:
    """Manages generation artifacts and their persistence."""

    def __init__(self, db_session: DbSession) -> None:
        self.db = db_session
        self.session_service = SessionService(db_session)

    def create_artifact(
        self,
        session_id: uuid.UUID,
        artifact_type: str,
        content: str,
        request: str,
        grounded: bool = False,
        provider: str | None = None,
        title: str | None = None,
    ) -> Artifact:
        """Persist a generated artifact.

        Validates session ownership implicitly via SessionService.
        """
        self.session_service.get_session(session_id)
        artifact = Artifact(
            session_id=session_id,
            artifact_type=artifact_type,
            content=content,
            request=request,
            grounded=grounded,
            provider=provider,
            title=title,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def get_artifact(self, session_id: uuid.UUID, artifact_id: uuid.UUID) -> Artifact | None:
        """Retrieve an artifact by ID, ensuring session isolation."""
        stmt = (
            select(Artifact)
            .where(Artifact.id == artifact_id)
            .where(Artifact.session_id == session_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_artifacts(self, session_id: uuid.UUID) -> list[Artifact]:
        """List all artifacts for a session."""
        stmt = (
            select(Artifact)
            .where(Artifact.session_id == session_id)
            .order_by(Artifact.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
