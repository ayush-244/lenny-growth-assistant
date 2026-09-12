"""Session database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Session(Base):
    """A conversational session."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[list["Message"]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
