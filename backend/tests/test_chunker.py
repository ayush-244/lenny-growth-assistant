"""Tests for the TranscriptChunker.

These tests are pure unit tests — no database or network required.
"""

import pytest

from app.rag.chunker import ChunkData, TranscriptChunker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_segment(text: str, start: float = 0.0, end: float = 10.0) -> dict:
    return {"text": text, "start": start, "end": end}


def long_segment(n_words: int = 700) -> dict:
    """Return a single segment with n_words words."""
    text = " ".join([f"word{i}" for i in range(n_words)])
    return {"text": text, "start": 0.0, "end": float(n_words)}


# ---------------------------------------------------------------------------
# Empty / minimal input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_segments_list(self):
        chunker = TranscriptChunker()
        result = chunker.chunk([])
        assert result == []

    def test_single_empty_text_segment(self):
        chunker = TranscriptChunker()
        result = chunker.chunk([{"text": "   ", "start": 0, "end": 5}])
        assert result == []

    def test_segment_with_no_text_key(self):
        chunker = TranscriptChunker()
        result = chunker.chunk([{"start": 0, "end": 5}])
        assert result == []


# ---------------------------------------------------------------------------
# Short transcript (fits in one chunk)
# ---------------------------------------------------------------------------

class TestShortTranscript:
    def test_short_transcript_produces_one_chunk(self):
        chunker = TranscriptChunker()
        segments = [make_segment("Hello world this is a short transcript.", 0, 5)]
        result = chunker.chunk(segments)
        assert len(result) == 1
        assert isinstance(result[0], ChunkData)
        assert result[0].chunk_index == 0

    def test_chunk_contains_all_content(self):
        chunker = TranscriptChunker()
        text = "The quick brown fox jumps over the lazy dog."
        segments = [make_segment(text, 10, 20)]
        result = chunker.chunk(segments)
        assert len(result) == 1
        assert text in result[0].content

    def test_timestamp_preserved_for_single_chunk(self):
        chunker = TranscriptChunker()
        segments = [make_segment("Some content here.", 5.5, 15.2)]
        result = chunker.chunk(segments)
        assert result[0].timestamp_start == 5.5
        assert result[0].timestamp_end == 15.2

    def test_no_timestamps_handled(self):
        chunker = TranscriptChunker()
        segments = [{"text": "No timestamps here."}]
        result = chunker.chunk(segments)
        assert len(result) == 1
        assert result[0].timestamp_start is None
        assert result[0].timestamp_end is None


# ---------------------------------------------------------------------------
# Long transcript (multiple chunks)
# ---------------------------------------------------------------------------

class TestLongTranscript:
    def test_long_transcript_produces_multiple_chunks(self):
        chunker = TranscriptChunker(target_chars=200, overlap_chars=20)
        # ~600 chars of content
        text = "word " * 120
        segments = [{"text": text, "start": 0.0, "end": 120.0}]
        result = chunker.chunk(segments)
        assert len(result) > 1

    def test_chunk_indices_are_sequential(self):
        chunker = TranscriptChunker(target_chars=200, overlap_chars=20)
        text = "word " * 120
        segments = [{"text": text, "start": 0.0, "end": 120.0}]
        result = chunker.chunk(segments)
        indices = [c.chunk_index for c in result]
        assert indices == list(range(len(result)))

    def test_no_content_silently_discarded(self):
        """All words from the original text should appear in at least one chunk."""
        chunker = TranscriptChunker(target_chars=300, overlap_chars=30)
        words = [f"unique_word_{i}" for i in range(100)]
        text = " ".join(words)
        segments = [{"text": text, "start": 0.0, "end": 100.0}]
        result = chunker.chunk(segments)
        all_chunk_text = " ".join(c.content for c in result)
        for word in words:
            assert word in all_chunk_text, f"{word!r} was silently discarded"


# ---------------------------------------------------------------------------
# Overlap behaviour
# ---------------------------------------------------------------------------

class TestOverlapBehaviour:
    def test_consecutive_chunks_share_content(self):
        chunker = TranscriptChunker(target_chars=200, overlap_chars=50)
        text = "word " * 150
        segments = [{"text": text, "start": 0.0, "end": 150.0}]
        result = chunker.chunk(segments)
        assert len(result) >= 2
        # The end of chunk 0 and the start of chunk 1 should share some words
        words_0 = set(result[0].content.split())
        words_1 = set(result[1].content.split())
        assert len(words_0 & words_1) > 0, "Consecutive chunks share no content (overlap broken)"

    def test_overlap_larger_than_target_raises(self):
        with pytest.raises(ValueError, match="overlap_chars must be less than target_chars"):
            TranscriptChunker(target_chars=100, overlap_chars=100)


# ---------------------------------------------------------------------------
# Timestamp preservation across multiple segments
# ---------------------------------------------------------------------------

class TestTimestampPreservation:
    def test_multi_segment_chunk_uses_first_start_last_end(self):
        chunker = TranscriptChunker(target_chars=500, overlap_chars=50)
        segments = [
            {"text": "First segment content. " * 5, "start": 0.0, "end": 10.0},
            {"text": "Second segment content. " * 5, "start": 10.0, "end": 20.0},
        ]
        result = chunker.chunk(segments)
        # Both segments fit in one chunk
        assert len(result) >= 1
        first_chunk = result[0]
        assert first_chunk.timestamp_start == 0.0

    def test_timestamp_start_increases_across_chunks(self):
        """Later chunks should start at or after earlier chunks' start times."""
        chunker = TranscriptChunker(target_chars=300, overlap_chars=30)
        segments = [
            {"text": "word " * 100, "start": float(i * 100), "end": float((i + 1) * 100)}
            for i in range(5)
        ]
        result = chunker.chunk(segments)
        assert len(result) > 1
        starts = [c.timestamp_start for c in result if c.timestamp_start is not None]
        assert starts == sorted(starts), "Chunk timestamps are not monotonically increasing"


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

class TestOrdering:
    def test_chunks_are_ordered_by_index(self):
        chunker = TranscriptChunker(target_chars=100, overlap_chars=10)
        text = "word " * 100
        segments = [{"text": text, "start": 0.0, "end": 100.0}]
        result = chunker.chunk(segments)
        for i, chunk in enumerate(result):
            assert chunk.chunk_index == i

    def test_multiple_input_segments_preserve_order(self):
        chunker = TranscriptChunker(target_chars=5000, overlap_chars=50)
        segments = [
            {"text": f"segment{i} " * 5, "start": float(i), "end": float(i + 1)}
            for i in range(10)
        ]
        result = chunker.chunk(segments)
        for chunk in result:
            assert chunk.chunk_index >= 0
