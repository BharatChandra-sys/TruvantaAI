# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
"""POST /message end to end, with the network (search, model, memory) stubbed out."""
import hashlib
import time

import pytest

import app.api as api
from app.auth import get_current_user
from app.cache import cache
from app.main import app
from app.models import User

ARTICLE = {"url": "https://example.org/a", "title": "A", "source": "example.org",
           "stance": "contradict", "model_stance": "contradict"}


@pytest.fixture()
def signed_in(client, monkeypatch):
    calls = {"search": 0, "remember": []}

    def search(text):
        calls["search"] += 1
        return [{"url": ARTICLE["url"], "title": "A", "text": "t", "kind": "news"}]

    monkeypatch.setattr("app.analysis.search.search_evidence", search)
    monkeypatch.setattr("app.analysis.ai.run_grounded_analysis",
                        lambda text, passages: {"verdict": "fake", "confidence": 0.9, "ai_score": 0.9, "model": "m"})
    monkeypatch.setattr("app.analysis.search.to_evidence",
                        lambda passages, grounded: (0.1, [ARTICLE["url"]], [dict(ARTICLE)], "Sources say no."))
    monkeypatch.setattr("app.retrieval.memory.lookup", lambda text: {"instant": None, "passages": []})
    monkeypatch.setattr("app.retrieval.memory.remember", lambda claim, result: calls["remember"].append((claim, result)))
    monkeypatch.setattr("app.analysis.cloud_models.get_inoculation", lambda text: None)
    app.dependency_overrides[get_current_user] = lambda: User(id=1, email="t@example.org", name="T")
    return client, calls


def _wait_for(calls, n):
    for _ in range(50):
        if len(calls["remember"]) >= n:
            return
        time.sleep(0.02)


def test_claim_is_checked_and_remembered(signed_in):
    client, calls = signed_in
    res = client.post("/message", json={"message": "Pipeline test claim one is true", "check": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_claim"] is True and body["verdict"] == "fake"
    assert body["evidence_articles"][0]["url"] == ARTICLE["url"]
    assert calls["search"] == 1
    _wait_for(calls, 1)
    claim, stored = calls["remember"][0]
    assert stored["verdict"] == "fake" and stored["basis"] == "sources"


def test_settled_answer_skips_search_and_memory_write(signed_in):
    client, calls = signed_in
    claim = "Pipeline test claim two is true"
    key = "stream:" + hashlib.sha256(" ".join(claim.lower().split()).encode()).hexdigest()
    cache.set(key, {"verdict": "real", "confidence": 0.92, "explanation": "Settled by the card.", "basis": "sources",
                    "ai_score": 0.1, "evidence_score": 0.9, "model": "m",
                    "evidence_articles": [dict(ARTICLE, stance="support", model_stance="support")]}, 60)
    res = client.post("/message", json={"message": claim, "check": True})
    assert res.status_code == 200, res.text
    assert res.json()["verdict"] == "real"
    assert res.json()["explanation"] == "Settled by the card."
    assert calls["search"] == 0
    time.sleep(0.1)
    assert calls["remember"] == []
