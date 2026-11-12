# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
"""Routes that spend free-tier quota or query the database need a signed-in user."""
import pytest

from app import middleware
from app.middleware import _get_limit


@pytest.mark.parametrize("method,path", [
    ("post", "/message"),
    ("post", "/check/stream"),
    ("post", "/explain"),
    ("post", "/audio/verify"),
    ("get", "/viral/dashboard"),
    ("get", "/analytics/trends/viral"),
    ("get", "/analytics/business/summary"),
    ("get", "/metrics"),
])
def test_signed_out_requests_are_refused(client, method, path):
    kwargs = {"json": {"message": "The earth is flat"}} if method == "post" else {}
    res = getattr(client, method)(path, **kwargs)
    assert res.status_code in (401, 403), f"{path} answered {res.status_code} without a token"


def test_health_ping_stays_public(client):
    assert client.get("/health/ping").status_code == 200


def test_stream_has_its_own_limit():
    (max_req, window), bucket = _get_limit("/check/stream")
    assert bucket == "/check/stream"
    assert max_req < middleware._DEFAULT_LIMIT[0]


def test_paths_in_one_route_group_share_a_bucket():
    assert _get_limit("/history/sessions/1")[1] == _get_limit("/history/sessions/2")[1]
    assert _get_limit("/viral/claim/abc")[1] == _get_limit("/viral/claim/def")[1] == "/viral"


def test_rate_limit_applies_across_paths(client, monkeypatch):
    monkeypatch.setattr(middleware, "_DEFAULT_LIMIT", (3, 60))
    middleware._store.clear()
    codes = [client.get(f"/viral/claim/{i}").status_code for i in range(5)]
    middleware._store.clear()
    assert codes[-1] == 429, codes
