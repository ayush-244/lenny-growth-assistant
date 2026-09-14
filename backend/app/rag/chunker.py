"""Transcript chunker for the Lenny Growth Assistant knowledge base.

Chunking strategy
-----------------

We approximate token count using the rule-of-thumb: 1 token ≈ 5 characters.

Normal transcript segments are grouped at semantic boundaries until the target
character budget is reached. A very long individual segment is split using a
sliding window with overlap.

Target chunk size : ~160 tokens → 800 characters
Overlap           : 0 characters for normal semantic chunks

Guarantees
----------

- chunk_index is 0-based and sequential.
- No content is silently discarded.
- Timestamps are preserved.
- Empty input returns an empty list.
- Transcript segment boundaries are preferred for normal chunks.
- Long individual segments retain overlapping sliding-window behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

TARGET_CHARS: int = 800
OVERLAP_CHARS: int = 0


@dataclass
class ChunkData:
    """Intermediate representation of a transcript chunk before DB persistence."""

    content: str
    chunk_index: int
    timestamp_start: float | None
    timestamp_end: float | None


@dataclass
class Segment:
    """A single timestamped segment from the raw transcript fixture."""

    text: str
    start: float | None
    end: float | None


class TranscriptChunker:
    """Splits transcript segments into semantically aware content chunks."""

    def __init__(
        self,
        target_chars: int = TARGET_CHARS,
        overlap_chars: int = OVERLAP_CHARS,
    ) -> None:
        if overlap_chars >= target_chars:
            raise ValueError("overlap_chars must be less than target_chars")

        self.target_chars = target_chars
        self.overlap_chars = overlap_chars

    def chunk(self, segments: list[dict]) -> list[ChunkData]:
        """Convert raw transcript segments into ChunkData objects."""

        if not segments:
            return []

        parsed = self._parse_segments(segments)

        if not parsed:
            return []

        return self._build_chunks(parsed)

    def _parse_segments(self, raw: list[dict]) -> list[Segment]:
        """Normalise raw segment dictionaries into Segment objects."""

        result: list[Segment] = []

        for seg in raw:
            text = (seg.get("text") or "").strip()

            if not text:
                continue

            result.append(
                Segment(
                    text=text,
                    start=seg.get("start"),
                    end=seg.get("end"),
                )
            )

        return result

    def _build_chunks(self, segments: list[Segment]) -> list[ChunkData]:
        """Build chunks while preferring transcript segment boundaries."""

        chunks: list[ChunkData] = []
        current_segments: list[Segment] = []
        current_chars = 0

        for segment in segments:
            segment_length = len(segment.text)

            # A single oversized segment needs character-based splitting.
            if segment_length > self.target_chars:
                if current_segments:
                    chunks.append(
                        self._make_segment_chunk(
                            current_segments,
                            len(chunks),
                        )
                    )
                    current_segments = []
                    current_chars = 0

                chunks.extend(
                    self._split_long_segment(
                        segment,
                        start_index=len(chunks),
                    )
                )
                continue

            separator_length = 1 if current_segments else 0
            proposed_length = (
                current_chars + separator_length + segment_length
            )

            if (
                current_segments
                and proposed_length > self.target_chars
            ):
                chunks.append(
                    self._make_segment_chunk(
                        current_segments,
                        len(chunks),
                    )
                )

                current_segments = [segment]
                current_chars = segment_length
            else:
                current_segments.append(segment)
                current_chars = proposed_length

        if current_segments:
            chunks.append(
                self._make_segment_chunk(
                    current_segments,
                    len(chunks),
                )
            )

        return chunks

    def _make_segment_chunk(
        self,
        segments: list[Segment],
        chunk_index: int,
    ) -> ChunkData:
        """Create a chunk from complete transcript segments."""

        content = " ".join(segment.text for segment in segments).strip()

        timestamp_start = next(
            (
                segment.start
                for segment in segments
                if segment.start is not None
            ),
            None,
        )

        timestamp_end = next(
            (
                segment.end
                for segment in reversed(segments)
                if segment.end is not None
            ),
            None,
        )

        logger.debug(
            "Emitted semantic chunk %d: segments=%d chars=%d ts=[%s, %s]",
            chunk_index,
            len(segments),
            len(content),
            timestamp_start,
            timestamp_end,
        )

        return ChunkData(
            content=content,
            chunk_index=chunk_index,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

    def _split_long_segment(
        self,
        segment: Segment,
        start_index: int,
    ) -> list[ChunkData]:
        """Split one oversized transcript segment with character overlap."""

        text = segment.text
        total = len(text)
        chunks: list[ChunkData] = []

        pos = 0

        while pos < total:
            end = min(pos + self.target_chars, total)

            if end < total:
                space = text.find(" ", end)

                if space != -1:
                    end = space

            content = text[pos:end].strip()

            if not content:
                break

            chunks.append(
                ChunkData(
                    content=content,
                    chunk_index=start_index + len(chunks),
                    timestamp_start=segment.start,
                    timestamp_end=segment.end,
                )
            )

            logger.debug(
                "Emitted long-segment chunk %d: chars [%d, %d) ts=[%s, %s]",
                start_index + len(chunks) - 1,
                pos,
                end,
                segment.start,
                segment.end,
            )

            if end >= total:
                break

            next_pos = end - self.overlap_chars

            if next_pos <= pos:
                next_pos = end

            pos = next_pos

        return chunks