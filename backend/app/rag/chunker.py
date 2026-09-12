"""Transcript chunker for the Lenny Growth Assistant knowledge base.

Chunking strategy
-----------------
We approximate token count using the rule-of-thumb: 1 token ≈ 5 characters.
This avoids a heavy tokenizer dependency while remaining consistent.

Target chunk size : ~500 tokens  → 2500 characters
Overlap           : ~50 tokens   → 250 characters

How it works
------------
1. Transcript segments are concatenated in order.
2. We slide a window over the full text, emitting a chunk whenever the
   accumulated character count reaches TARGET_CHARS.
3. The next chunk starts OVERLAP_CHARS before the previous one ended,
   so consecutive chunks share context.
4. For multi-segment chunks: timestamp_start = first segment's start,
   timestamp_end = last segment's end.
5. Short transcripts that fit in one chunk are emitted as a single chunk.
6. Empty input returns an empty list — never raises.

Guarantees
----------
- chunk_index is 0-based and sequential.
- No content is silently discarded.
- Timestamps are always preserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ~500 tokens × 5 chars/token
TARGET_CHARS: int = 2500
# ~50 tokens × 5 chars/token
OVERLAP_CHARS: int = 250


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
    """Splits transcript segments into overlapping content chunks.

    Parameters
    ----------
    target_chars:
        Approximate character budget per chunk (default 2500 ≈ 500 tokens).
    overlap_chars:
        Overlap in characters between consecutive chunks (default 250 ≈ 50 tokens).
    """

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
        """Convert raw transcript segments into overlapping ChunkData objects.

        Parameters
        ----------
        segments:
            List of dicts with keys: ``text``, ``start`` (optional), ``end`` (optional).

        Returns
        -------
        list[ChunkData]
            Ordered list of chunks. Empty list if ``segments`` is empty or
            all segment text is whitespace-only.
        """
        if not segments:
            return []

        parsed = self._parse_segments(segments)
        if not parsed:
            return []

        return self._build_chunks(parsed)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_segments(self, raw: list[dict]) -> list[Segment]:
        """Normalise raw segment dicts into Segment objects."""
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
        """Slide a window over the segment list, emitting chunks."""
        # Flatten all text into a single string with segment boundaries tracked.
        # We track which character positions correspond to which segment's timestamps.
        full_text = ""
        # List of (char_start, char_end, seg_start, seg_end) for each segment
        seg_map: list[tuple[int, int, float | None, float | None]] = []
        for seg in segments:
            c_start = len(full_text)
            full_text += seg.text + " "
            c_end = len(full_text)
            seg_map.append((c_start, c_end, seg.start, seg.end))

        full_text = full_text.rstrip()
        total = len(full_text)

        if total == 0:
            return []

        chunks: list[ChunkData] = []
        pos = 0
        chunk_index = 0

        while pos < total:
            end = min(pos + self.target_chars, total)

            # Don't cut in the middle of a word — advance to next space
            if end < total:
                space = full_text.find(" ", end)
                if space != -1:
                    end = space

            content = full_text[pos:end].strip()
            if not content:
                break

            ts_start, ts_end = self._timestamps_for_range(seg_map, pos, end)

            chunks.append(
                ChunkData(
                    content=content,
                    chunk_index=chunk_index,
                    timestamp_start=ts_start,
                    timestamp_end=ts_end,
                )
            )
            chunk_index += 1
            logger.debug(
                "Emitted chunk %d: chars [%d, %d) ts=[%s, %s]",
                chunk_index - 1,
                pos,
                end,
                ts_start,
                ts_end,
            )

            if end >= total:
                break

            # Advance with overlap
            pos = end - self.overlap_chars
            if pos <= 0:
                break

        return chunks

    def _timestamps_for_range(
        self,
        seg_map: list[tuple[int, int, float | None, float | None]],
        char_start: int,
        char_end: int,
    ) -> tuple[float | None, float | None]:
        """Return (first_seg_start, last_seg_end) for segments overlapping [char_start, char_end)."""
        ts_start: float | None = None
        ts_end: float | None = None
        for c_s, c_e, s_start, s_end in seg_map:
            # Segment overlaps with the chunk window
            if c_e > char_start and c_s < char_end:
                if ts_start is None and s_start is not None:
                    ts_start = s_start
                if s_end is not None:
                    ts_end = s_end
        return ts_start, ts_end
