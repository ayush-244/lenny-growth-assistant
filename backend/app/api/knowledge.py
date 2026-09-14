from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.models.chunk import Chunk
from app.models.transcript import Transcript
from app.schemas.knowledge import (
    KnowledgeChunkResponse,
    KnowledgeEpisodeResponse,
)

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


@router.get("", response_model=list[KnowledgeEpisodeResponse])
def list_knowledge_base(db: Session = Depends(get_db)):
    transcripts = (
        db.query(Transcript)
        .options(selectinload(Transcript.chunks))
        .order_by(Transcript.ingested_at.desc())
        .all()
    )

    return [
        KnowledgeEpisodeResponse(
            id=transcript.id,
            episode_id=transcript.episode_id,
            title=transcript.title,
            guest_name=transcript.guest_name,
            source_url=transcript.source_url,
            ingested_at=transcript.ingested_at,
            chunk_count=len(transcript.chunks),
            chunks=[
                KnowledgeChunkResponse(
                    id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    timestamp_start=chunk.timestamp_start,
                    timestamp_end=chunk.timestamp_end,
                )
                for chunk in sorted(
                    transcript.chunks,
                    key=lambda item: item.chunk_index,
                )
            ],
        )
        for transcript in transcripts
    ]