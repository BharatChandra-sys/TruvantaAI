"""Local cross-encoder reranking, its backends, and the LLM fallback."""
import sys
import types

import numpy as np
import pytest

import app.analysis.cross_encoder as cross_encoder
import app.retrieval.reranker as reranker


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    """Each test decides the backend again."""
    monkeypatch.setattr(reranker, "_backend", None)
    monkeypatch.setattr(reranker, "_predict", None)
    monkeypatch.delenv("RERANKER_BACKEND", raising=False)


def _use_model(monkeypatch, scores: dict):
    """A loaded backend whose score for each text is looked up by its first word."""
    monkeypatch.setattr(reranker, "_backend", "fake")
    monkeypatch.setattr(reranker, "_predict",
                        lambda q, texts: np.array([scores.get(t.split()[0], 0.0) for t in texts]))


def test_off_means_no_scores(monkeypatch):
    monkeypatch.setenv("RERANKER_BACKEND", "off")
    assert not reranker.available() and reranker.score("claim", ["text"]) is None


def test_an_unknown_backend_is_off(monkeypatch):
    monkeypatch.setenv("RERANKER_BACKEND", "bert-large")
    assert reranker.backend() == "off"


def test_auto_falls_through_to_the_next_installed_backend(monkeypatch):
    def missing():
        raise ImportError("no fastembed")
    monkeypatch.setitem(reranker._LOADERS, "fastembed", missing)
    monkeypatch.setitem(reranker._LOADERS, "sentence-transformers", lambda: (lambda q, t: np.ones(len(t))))
    assert reranker.backend() == "sentence-transformers"


def test_fastembed_logits_become_probabilities(monkeypatch):
    class TextCrossEncoder:
        def __init__(self, name):
            assert name == "Xenova/ms-marco-MiniLM-L-6-v2"

        def rerank(self, query, texts):
            return iter([0.0, 4.0, -4.0][:len(texts)])

    module = types.ModuleType("fastembed.rerank.cross_encoder")
    module.TextCrossEncoder = TextCrossEncoder
    for name in ("fastembed", "fastembed.rerank"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "fastembed.rerank.cross_encoder", module)
    monkeypatch.setenv("RERANKER_BACKEND", "fastembed")

    assert reranker.score("claim", ["a", "b", "c"]) == [0.5, 0.982, 0.018]


def test_a_scoring_error_returns_none(monkeypatch):
    monkeypatch.setattr(reranker, "_backend", "fake")
    monkeypatch.setattr(reranker, "_predict", lambda q, t: (_ for _ in ()).throw(RuntimeError("onnx")))
    assert reranker.score("claim", ["text"]) is None


def test_rerank_orders_by_score_and_keeps_ties_in_retrieval_order(monkeypatch):
    _use_model(monkeypatch, {"high": 0.9, "mid": 0.5, "low": 0.1})
    pool = [{"claim_text": t} for t in ("low a", "mid b", "high c", "mid d", "low e")]
    ranked = reranker.rerank("claim", pool, top_k=3)
    assert [c["claim_text"] for c in ranked] == ["high c", "mid b", "mid d"]
    assert ranked[0]["rerank_score"] == 0.9


def test_articles_are_ranked_locally_and_only_kept_ones_cost_an_llm_call(monkeypatch):
    _use_model(monkeypatch, {"Relevant": 0.95, "Related": 0.6, "Off-topic": 0.01})
    asked = []

    def llm(claim, article):
        asked.append(article["title"])
        return {"relevance": 0.0, "stance": "contradict", "reason": "denies it"}
    monkeypatch.setattr(cross_encoder, "_score_article", llm)

    articles = [{"title": t, "description": "", "stance": "neutral"}
                for t in ("Off-topic 1", "Relevant 1", "Off-topic 2", "Related 1", "Off-topic 3")]
    kept = cross_encoder.rerank_articles("claim", articles, top_k=2)

    assert [a["title"] for a in kept] == ["Relevant 1", "Related 1"]
    assert sorted(asked) == ["Related 1", "Relevant 1"]
    # Relevance is the model's, not overwritten by the LLM; stance is the LLM's.
    assert kept[0]["relevance_score"] == 0.95 and kept[0]["stance"] == "contradict"


def test_without_a_local_model_the_llm_scores_every_article(monkeypatch):
    monkeypatch.setenv("RERANKER_BACKEND", "off")
    scores = {"A": 0.2, "B": 0.9, "C": 0.5}
    monkeypatch.setattr(cross_encoder, "_score_article",
                        lambda claim, a: {"relevance": scores[a["title"]], "stance": "support", "reason": ""})
    articles = [{"title": t} for t in "ABC"]
    assert [a["title"] for a in cross_encoder.rerank_articles("claim", articles, top_k=2)] == ["B", "C"]


def test_small_lists_are_returned_untouched(monkeypatch):
    monkeypatch.setattr(cross_encoder, "_score_article", lambda *a: pytest.fail("no call expected"))
    articles = [{"title": "A"}, {"title": "B"}]
    assert cross_encoder.rerank_articles("claim", articles, top_k=5) is articles
