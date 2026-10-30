"""Embedding backend choice, and that vectors from different models never mix."""
import importlib


def _fresh(monkeypatch, **env):
    import app.retrieval.embeddings as e
    for k in ("EMBEDDINGS_BACKEND", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return importlib.reload(e)


def test_gemini_is_the_default_when_a_key_is_set(monkeypatch):
    e = _fresh(monkeypatch, GEMINI_API_KEY="k")
    assert e.backend() == "gemini" and e.model_id() == "gemini-embedding-001@384"
    assert e.thresholds() == {"match": 0.97, "related": 0.85}


def test_off_means_no_vectors(monkeypatch):
    e = _fresh(monkeypatch, EMBEDDINGS_BACKEND="off")
    assert not e.available() and e.embed("anything") is None and e.model_id() is None


def test_a_failed_remote_call_returns_none(monkeypatch):
    e = _fresh(monkeypatch, GEMINI_API_KEY="k")
    monkeypatch.setattr(e, "_gemini_encode", lambda texts: (_ for _ in ()).throw(TimeoutError("slow")))
    assert e.embed("Octopuses have three hearts.") is None


def test_memory_rows_are_tagged_with_their_vector_space(monkeypatch):
    _fresh(monkeypatch, GEMINI_API_KEY="k")
    from app.retrieval import memory
    assert memory._space() == "stream|gemini-embedding-001@384"
    assert memory._thresholds() == (0.97, 0.85)
