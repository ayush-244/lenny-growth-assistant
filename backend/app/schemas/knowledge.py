from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class KnowledgeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    content: str
    timestamp_start: float | None
    timestamp_end: float | None


class KnowledgeEpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    episode_id: str
    title: str
    guest_name: str | None
    source_url: str | None
    ingested_at: datetime
    chunk_count: int
    chunks: list[KnowledgeChunkResponse]