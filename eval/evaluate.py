import json
import time
from typing import Dict, Any
import uuid

from fastapi.testclient import TestClient
from _pytest.monkeypatch import MonkeyPatch

from app.main import app
from app.llm.base import LLMProvider, LLMResponse

class DeterministicMockProvider(LLMProvider):
    def __init__(self):
        self.invalid_citation_attempts = 0

    def chat(self, messages: list[dict[str, str]], system_prompt: str | None = None, tools: list[dict[str, Any]] | None = None, tool_executor: Any = None) -> LLMResponse:
        prompt_text = " ".join([m.get("content", "") for m in messages if isinstance(m.get("content"), str)]).lower()
        user_prompt = " ".join([m.get("content", "") for m in messages if isinstance(m.get("content"), str)]).lower()
        if system_prompt:
            prompt_text += " " + system_prompt.lower()

        if "spacex" in user_prompt:
            return LLMResponse(
                content="I don't have enough evidence in the available Lenny sources to answer that.",
                provider="mock",
                model="mock",
                tool_calls_made=0
            )

        if "double invalid citation behavior" in user_prompt:
            essay = "Word " * 1250
            return LLMResponse(
                content=f"{essay}\n---\nCITATIONS: invalid-id-123\nWORD_COUNT: 1250",
                provider="mock",
                model="mock",
                tool_calls_made=0
            )

        if "invalid citation behavior" in user_prompt:
            self.invalid_citation_attempts += 1
            essay = "Word " * 1250
            if self.invalid_citation_attempts == 2:
                # Return valid second attempt
                return LLMResponse(
                    content=f"{essay}\n---\nCITATIONS: 00000000-0000-0000-0000-000000000001\nWORD_COUNT: 1250",
                    provider="mock",
                    model="mock",
                    tool_calls_made=0
                )
            else:
                return LLMResponse(
                    content=f"{essay}\n---\nCITATIONS: invalid-id-123\nWORD_COUNT: 1250",
                    provider="mock",
                    model="mock",
                    tool_calls_made=0
                )

        if "ship 30 for 30 essay" in user_prompt or ("essay" in user_prompt and "airbnb" in user_prompt):
            essay = "Word " * 1250
            return LLMResponse(
                content=f"{essay}\n---\nCITATIONS: 00000000-0000-0000-0000-000000000001\nWORD_COUNT: 1250",
                provider="mock",
                model="mock",
                tool_calls_made=0
            )

        if "markdown artifact" in user_prompt or "checklist" in user_prompt:
            if tool_executor:
                tool_executor("generate_artifact", {"type": "markdown", "content": "# Checklist"})
            return LLMResponse(
                content="Here is your artifact.",
                provider="mock",
                model="mock",
                tool_calls_made=1
            )

        if "html artifact" in user_prompt or "visual layout" in user_prompt:
            if tool_executor:
                tool_executor("generate_artifact", {"type": "html", "content": "<div>Layout</div>"})
            return LLMResponse(
                content="Here is your artifact.",
                provider="mock",
                model="mock",
                tool_calls_made=1
            )

        has_retrieval_tool = False
        if tools:
            for t in tools:
                if t.get("name") == "retrieve_knowledge" or t.get("function", {}).get("name") == "retrieve_knowledge":
                    has_retrieval_tool = True
                    break

        if "brian chesky" in user_prompt:
            if tool_executor and has_retrieval_tool:
                tool_executor("retrieve_knowledge", {"query": "brian chesky airbnb growth"})
            return LLMResponse(
                content="Brian Chesky approached Airbnb's early growth by doing X. [00000000-0000-0000-0000-000000000001]",
                provider="mock",
                model="mock",
                tool_calls_made=1
            )

        if "invalid id behavior" in user_prompt:
            if tool_executor and has_retrieval_tool:
                tool_executor("retrieve_knowledge", {"query": "test"})
            return LLMResponse(
                content="This cites a fake ID. [99999999-9999-9999-9999-999999999999]",
                provider="mock",
                model="mock",
                tool_calls_made=1
            )

        if "no citation behavior" in user_prompt:
            if tool_executor and has_retrieval_tool:
                tool_executor("retrieve_knowledge", {"query": "test"})
            return LLMResponse(
                content="This is an answer with no citations.",
                provider="mock",
                model="mock",
                tool_calls_made=1
            )

        if tool_executor and has_retrieval_tool:
            tool_executor("retrieve_knowledge", {"query": "test"})

        # Standard factual
        return LLMResponse(
            content="Alex Rivera said X about pricing. [00000000-0000-0000-0000-000000000001]",
            provider="mock",
            model="mock",
            tool_calls_made=1
        )

def run_evaluation():
    print("Starting Deterministic Evaluation Harness...")

    mp = MonkeyPatch()
    mock_provider_instance = DeterministicMockProvider()
    def mock_get_provider(*args, **kwargs):
        return mock_provider_instance

    mp.setattr("app.llm.router.LLMRouter.get_provider", mock_get_provider)
    mp.setattr("app.llm.get_llm_provider", mock_get_provider)

    from app.schemas.retrieval import RetrievalResponse, RetrievalResult

    from app.rag.retriever import Retriever

    def mock_retrieve(self, query: str, *args, **kwargs):
        if "spacex" in query.lower():
            return RetrievalResponse(query=query, results=[], total_found=0, threshold_applied=0.5)

        # Return 3 results for Ship30 to pass MIN_EVIDENCE_CHUNKS (usually 3)
        return RetrievalResponse(
            query=query,
            results=[
                RetrievalResult(
                    chunk_id=uuid.UUID(int=1),
                    transcript_id=uuid.UUID(int=2),
                    content="Mock evidence content 1",
                    similarity_score=0.9,
                    episode_id="episode_1",
                    title="Mock Title",
                    guest_name="Mock Guest",
                    source_url="http://mock",
                    timestamp_start=0,
                    timestamp_end=10,
                    chunk_index=0
                ),
                RetrievalResult(
                    chunk_id=uuid.UUID(int=2),
                    transcript_id=uuid.UUID(int=3),
                    content="Mock evidence content 2",
                    similarity_score=0.8,
                    episode_id="episode_1",
                    title="Mock Title",
                    guest_name="Mock Guest",
                    source_url="http://mock",
                    timestamp_start=10,
                    timestamp_end=20,
                    chunk_index=1
                ),
                RetrievalResult(
                    chunk_id=uuid.UUID(int=3),
                    transcript_id=uuid.UUID(int=4),
                    content="Mock evidence content 3",
                    similarity_score=0.7,
                    episode_id="episode_1",
                    title="Mock Title",
                    guest_name="Mock Guest",
                    source_url="http://mock",
                    timestamp_start=20,
                    timestamp_end=30,
                    chunk_index=2
                )
            ],
            total_found=3,
            threshold_applied=0.5
        )

    mp.setattr(Retriever, "retrieve", mock_retrieve)

    class MockEmbeddingProvider:
        def embed(self, text): return [0.0]*768
    def mock_get_embedding_provider(*args, **kwargs): return MockEmbeddingProvider()
    mp.setattr("app.rag.embeddings.get_embedding_provider", mock_get_embedding_provider)

    client = TestClient(app)

    with open("eval/questions.json", "r") as f:
        questions = json.load(f)

    session_id = None
    results = {
        "total": len(questions) + 1,
        "passed": 0,
        "failed": 0,
        "groundedness": {"grounded": 0, "insufficient_context": 0, "error": 0},
        "artifacts": 0,
        "ship30": 0,
        "citation_validation": 0,
        "session_isolation_tested": False
    }

    try:
        resp = client.post("/sessions")
        resp.raise_for_status()
        session_id = resp.json()["id"]
    except Exception as e:
        print(f"Failed to create session: {e}")
        return

    for q in questions:
        qid = q["id"]
        print(f"--- Running Case: {qid} ---")
        try:
            if q["type"] == "message":
                res = client.post(
                    f"/sessions/{session_id}/messages",
                    json={"content": q["query"]}
                )
                res.raise_for_status()
                data = res.json()

                if qid == "case_a_factual" or qid == "case_b_multiturn":
                    assert data["grounded"] is True, f"Expected grounded=True for {qid}"
                    assert "00000000-0000-0000-0000-000000000001" in data["content"], f"Expected citation in content for {qid}"
                    results["groundedness"]["grounded"] += 1

                if qid == "case_c_insufficient":
                    assert data["grounded"] is False, "Expected grounded=False for out of corpus"
                    assert "00000000" not in data["content"], "Should not have citations"
                    results["groundedness"]["insufficient_context"] += 1

                if qid in ["case_j_unsupported", "case_k_invalid_id", "case_l_no_citation"]:
                    assert data["grounded"] is False, f"Expected grounded=False for {qid}"
                    assert len(data.get("citations", [])) == 0, f"Expected citations=[] for {qid}"
                    assert "I don't have enough evidence" in data["content"], f"Expected fallback response for {qid}"
                    results["groundedness"]["insufficient_context"] += 1

                print(f"PASS {qid}")
                results["passed"] += 1

            elif q["type"] == "essay":
                res = client.post(
                    f"/sessions/{session_id}/essay",
                    json={"content": q["query"]}
                )
                res.raise_for_status()
                data = res.json()

                if qid == "case_d_ship30":
                    assert data["grounded"] is True, "Expected grounded=True"
                    assert 1100 <= data["word_count"] <= 1400, "Word count not in range"
                    assert len(data.get("validation_issues", [])) == 0, "Expected no issues"
                    results["ship30"] += 1

                if qid == "case_e_invalid_citation":
                    assert data["grounded"] is True, "Expected grounded=True after retry"
                    assert data.get("generation_attempts", 1) == 2, "Expected exactly 2 attempts"
                    assert len(data.get("validation_issues", [])) == 0, "Expected no final issues"
                    results["citation_validation"] += 1

                if qid == "case_f_invalid_citation_fallback":
                    assert data["grounded"] is False, "Expected fallback to be ungrounded"
                    assert data.get("generation_attempts", 1) == 2, "Expected exactly 2 attempts"
                    # In python, finding a substring in the list elements
                    issues = data.get("validation_issues", [])
                    assert any("invalid_citations" in i for i in issues), "Expected invalid citations issue"
                    assert (data.get("word_count", 0) or 0) < 50, "Expected safe fallback content without prose"
                    results["citation_validation"] += 1

                print(f"PASS {qid}")
                results["passed"] += 1

            elif q["type"] == "artifact":
                res = client.post(
                    f"/sessions/{session_id}/artifacts",
                    json={"request": q["query"], "artifact_type": q["artifact_type"]}
                )
                res.raise_for_status()
                data = res.json()

                assert data["artifact_type"] == q["artifact_type"], "Artifact type mismatch"
                assert len(data["content"]) > 0, "Empty content"

                if q["artifact_type"] == "html":
                    assert "Content-Security-Policy" in data["content"], "CSP missing from HTML"

                # Verify persistence
                arts = client.get(f"/sessions/{session_id}/artifacts").json()
                assert any(a["id"] == data["id"] for a in arts), "Artifact not persisted"

                results["artifacts"] += 1
                print(f"PASS {qid}")
                results["passed"] += 1

        except Exception as e:
            print(f"FAILED {qid}: {str(e)}")
            results["failed"] += 1

    # Test Session Isolation
    qid = "case_i_session_isolation"
    print(f"--- Running Case: {qid} ---")
    try:
        resp = client.post("/sessions")
        session_b = resp.json()["id"]

        arts = client.get(f"/sessions/{session_b}/artifacts").json()
        assert len(arts) == 0, "Artifacts leaked across sessions"

        results["session_isolation_tested"] = True
        print(f"PASS {qid}")
        results["passed"] += 1
    except Exception as e:
        print(f"FAILED {qid}: {str(e)}")
        results["failed"] += 1

    print("\nTotal cases:", results['total'])
    print("Passed:", results['passed'])
    print("Failed:", results['failed'])
    print("\nGroundedness summary:", results['groundedness'])
    print("Ship30 summary:", results['ship30'])
    print("Artifact summary:", results['artifacts'])
    print("Citation validation summary:", results['citation_validation'])
    print("Session isolation summary:", results['session_isolation_tested'])

if __name__ == "__main__":
    run_evaluation()
