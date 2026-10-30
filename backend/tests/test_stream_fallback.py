"""The live check answers from established knowledge only when nothing found addresses the claim."""
import json
import uuid

import pytest


def _verdict(monkeypatch, passages, grounded, knowledge):
    import app.analysis.ai as ai
    import app.analysis.search as search
    from app.routes import stream_routes

    monkeypatch.setattr(search, "iter_search", lambda text: iter([("done", passages)]))
    monkeypatch.setattr(ai, "run_grounded_analysis", lambda claim, p: grounded)
    calls = []
    monkeypatch.setattr(ai, "run_knowledge_analysis", lambda claim: calls.append(claim) or knowledge)
    monkeypatch.setattr(stream_routes, "_persist", lambda *a: None)

    claim = f"test claim {uuid.uuid4()}"   # unique, so the stream cache never answers
    events = list(stream_routes._run(claim, None))
    verdict = next(json.loads(e.split("data: ", 1)[1]) for e in events if e.startswith("event: verdict"))
    return verdict, calls


KNOWS = {"verdict": "real", "confidence": 0.7, "explanation": "The Sun is a G-type star.",
         "ai_score": 0.15, "model": "test"}

PASSAGE = {"kind": "reference", "title": "Sun", "url": "https://en.wikipedia.org/wiki/Sun",
           "source": "Wikipedia", "text": "The Sun", "rating": "", "low_trust": False}


def test_no_sources_answers_from_knowledge(monkeypatch):
    v, calls = _verdict(monkeypatch, [], None, KNOWS)
    assert calls and v["verdict"] == "real" and v["basis"] == "knowledge"
    assert v["confidence"] <= 0.7 and v["grounded"] is False


def test_sources_that_do_not_address_the_claim_fall_back_to_knowledge(monkeypatch):
    grounded = {"verdict": "uncertain", "confidence": 0.5, "explanation": "None address it.",
                "stances": {1: "neutral"}, "ai_score": 0.5, "model": "test"}
    v, calls = _verdict(monkeypatch, [PASSAGE], grounded, KNOWS)
    assert calls and v["basis"] == "knowledge" and v["verdict"] == "real"


def test_mixed_sources_stay_uncertain(monkeypatch):
    grounded = {"verdict": "uncertain", "confidence": 0.5, "explanation": "Sources disagree [1][2].",
                "stances": {1: "support", 2: "refute"}, "ai_score": 0.5, "model": "test"}
    v, calls = _verdict(monkeypatch, [PASSAGE, dict(PASSAGE, url="https://x.org/a", source="X")], grounded, KNOWS)
    # The early answer was computed, but disagreeing sources keep the verdict uncertain.
    assert v["verdict"] == "uncertain" and v["basis"] == "sources"


def test_model_unsure_from_knowledge_stays_uncertain(monkeypatch):
    unsure = dict(KNOWS, verdict="uncertain", confidence=0.5)
    v, _ = _verdict(monkeypatch, [], None, unsure)
    assert v["verdict"] == "uncertain" and v["basis"] == "sources"


def test_early_answer_streams_before_the_sourced_verdict(monkeypatch):
    import time
    import app.analysis.ai as ai
    import app.analysis.search as search
    from app.routes import stream_routes

    def slow_judge(claim, passages):
        time.sleep(0.4)          # the model reading sources takes a while
        return {"verdict": "fake", "confidence": 0.93, "explanation": "Refuted [1].",
                "stances": {1: "refute"}, "ai_score": 0.9, "model": "test"}

    monkeypatch.setattr(search, "iter_search", lambda text: iter([("done", [PASSAGE])]))
    monkeypatch.setattr(ai, "run_grounded_analysis", slow_judge)
    monkeypatch.setattr(ai, "run_knowledge_analysis", lambda claim: dict(KNOWS, verdict="fake", confidence=0.7))
    monkeypatch.setattr(stream_routes, "_persist", lambda *a: None)

    events = [e.split("\n", 1)[0] for e in stream_routes._run(f"claim {uuid.uuid4()}", None)]
    assert "event: early" in events
    assert events.index("event: early") < events.index("event: verdict")


def test_sources_no_model_could_read_fall_back_to_the_early_answer(monkeypatch):
    # Seen in the evaluation: every provider rate-limited, the early answer was right
    # but the final verdict said "uncertain".
    v, calls = _verdict(monkeypatch, [PASSAGE], None, KNOWS)
    assert v["verdict"] == "real" and v["basis"] == "knowledge" and v["sources_unread"] is True
    assert v["confidence"] <= 0.7


def test_early_answer_can_be_switched_off(monkeypatch):
    import app.analysis.ai as ai
    import app.analysis.search as search
    from app.routes import stream_routes

    monkeypatch.setattr(stream_routes, "EARLY_ANSWER", False)
    monkeypatch.setattr(search, "iter_search", lambda text: iter([("done", [PASSAGE])]))
    monkeypatch.setattr(ai, "run_grounded_analysis", lambda c, p: {
        "verdict": "fake", "confidence": 0.93, "explanation": "Refuted [1].",
        "stances": {1: "refute"}, "ai_score": 0.9, "model": "test"})
    calls = []
    monkeypatch.setattr(ai, "run_knowledge_analysis", lambda c: calls.append(c) or KNOWS)
    monkeypatch.setattr(stream_routes, "_persist", lambda *a: None)

    events = [e.split("\n", 1)[0] for e in stream_routes._run(f"claim {uuid.uuid4()}", None)]
    assert "event: early" not in events and not calls      # no extra model call at all
