"""Claim memory: when a stored check may answer a new claim, and when it is stored as verified."""
import json
import uuid

from app.retrieval.memory import _status, claim_key, confirm, same_meaning, same_wording


def test_claim_key_ignores_case_spacing_and_punctuation():
    assert claim_key("India's Chandrayaan-3 landed in 2023.") == claim_key("india's  chandrayaan-3 landed in 2023")


def test_negation_blocks_a_match():
    assert not same_meaning("Vaccines cause autism.", "Vaccines do not cause autism.")
    assert not same_meaning("The vaccine causes autism", "The vaccine doesn't cause autism")
    assert same_meaning("Vaccines cause autism", "Vaccination causes autism in children")


def test_different_numbers_block_a_match():
    assert not same_meaning("The UK voted to leave the EU in 2016", "The UK voted to leave the EU in 2019")
    assert same_meaning("Brexit vote happened in 2016", "In 2016 the UK held the Brexit referendum")


def test_reordered_claim_is_never_answered_from_memory():
    # These embed at 0.966: only the word order says they are opposites.
    assert not same_wording("Light travels faster than sound.", "Sound travels faster than light.")
    assert same_wording("Vaccines cause autism.", "Vaccines are a cause of autism")
    assert not same_wording("Bill Gates founded Apple.", "Steve Jobs founded Apple.")


def _arts(*stances):
    return [{"model_stance": s, "kind": "news", "stance": s} for s in stances]


def test_verified_needs_two_agreeing_sources_and_none_against():
    ok = {"basis": "sources", "verdict": "fake", "confidence": 0.93, "evidence_articles": _arts("contradict", "contradict", "neutral")}
    assert _status(ok) == "verified"
    assert _status(dict(ok, evidence_articles=_arts("contradict", "support", "contradict"))) == "model_only"
    assert _status(dict(ok, evidence_articles=_arts("contradict"))) == "model_only"
    assert _status(dict(ok, confidence=0.7)) == "model_only"
    assert _status(dict(ok, basis="knowledge")) == "model_only"


def test_stream_answers_from_memory_without_waiting_for_search(monkeypatch):
    import app.analysis.ai as ai
    import app.analysis.search as search
    import app.retrieval.memory as memory
    from app.routes import stream_routes

    hit = {"verdict": "fake", "confidence": 0.93, "explanation": "Refuted [1].",
           "evidence_articles": [{"url": "https://snopes.com/x", "title": "X", "source": "Snopes", "kind": "fact_check"}],
           "basis": "sources", "memory": {"claim": "earlier wording", "similarity": 0.95, "checked_at": None}}

    def slow_search(text):
        import time
        time.sleep(0.05)
        yield ("sources", [{"url": "https://a.org", "title": "A", "source": "A", "kind": "news", "rating": ""}])
        yield ("done", [])

    judged = []
    monkeypatch.setattr(memory, "lookup", lambda claim: {"instant": hit, "passages": []})
    monkeypatch.setattr(search, "iter_search", slow_search)
    monkeypatch.setattr(ai, "run_grounded_analysis", lambda c, p: judged.append(c))
    monkeypatch.setattr(stream_routes, "_persist", lambda *a: None)

    events = list(stream_routes._run(f"claim {uuid.uuid4()}", None))
    verdict = next(json.loads(e.split("data: ", 1)[1]) for e in events if e.startswith("event: verdict"))
    assert verdict["verdict"] == "fake" and verdict["memory"]["similarity"] == 0.95
    assert not judged    # the model was never asked


def test_related_memory_sources_reach_the_model_as_passages(monkeypatch):
    import app.analysis.ai as ai
    import app.analysis.search as search
    import app.retrieval.memory as memory
    from app.routes import stream_routes

    remembered = {"kind": "fact_check", "url": "https://factcheck.org/old", "title": "Old check",
                  "source": "FactCheck.org", "text": "Rated false.", "rating": "False",
                  "published": "", "low_trust": False, "from_memory": True}
    seen = []
    monkeypatch.setattr(memory, "lookup", lambda claim: {"instant": None, "passages": [remembered]})
    monkeypatch.setattr(search, "iter_search", lambda text: iter([("done", [])]))
    monkeypatch.setattr(ai, "run_grounded_analysis", lambda c, p: seen.extend(p) or None)
    monkeypatch.setattr(ai, "run_knowledge_analysis", lambda c: None)
    monkeypatch.setattr(stream_routes, "_persist", lambda *a: None)

    list(stream_routes._run(f"claim {uuid.uuid4()}", None))
    assert [p["url"] for p in seen] == ["https://factcheck.org/old"]


def test_one_check_is_never_enough_for_an_instant_answer():
    # Seen in the evaluation: a 7B model's misreading was stored as VERIFIED.
    assert confirm(None, None, 1, "real", "verified") == ("verified", 1)
    assert confirm("real", "verified", 1, "real", "verified") == ("verified", 2)


def test_quick_repeats_do_not_confirm_a_verdict():
    # Seen in the evaluation: the same misreading, repeated minutes apart, confirmed itself.
    assert confirm("real", "verified", 1, "real", "verified", hours_since=0.2) == ("verified", 1)
    assert confirm("real", "verified", 1, "real", "verified", hours_since=13) == ("verified", 2)


def test_a_disagreeing_check_disputes_the_stored_verdict():
    assert confirm("real", "verified", 3, "fake", "verified") == ("disputed", 1)
    assert confirm("real", "disputed", 1, "real", "verified") == ("verified", 2)


def test_a_person_review_is_kept():
    assert confirm("fake", "human_reviewed", 1, "real", "verified") == ("human_reviewed", 1)
