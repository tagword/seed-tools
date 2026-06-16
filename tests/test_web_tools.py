from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import seed_tools.web as web_mod
from seed_tools.web import web_fetch_handler, web_search_handler


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            return self._data
        return self._data[:size]


def test_web_fetch_caps_body_bytes(monkeypatch) -> None:
    monkeypatch.setenv("SEED_WEB_FETCH_MAX_BYTES", "10")
    monkeypatch.setenv("SEED_WEB_FETCH_CHUNK_SUMMARY", "0")
    monkeypatch.setattr(web_mod, "_artifact_write_text", lambda **kwargs: "")
    payload = b"a" * 40000
    with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
        out = web_fetch_handler("https://example.com")
    assert "body truncated after 32768 bytes" in out


def test_web_search_clamps_num_results_and_dedup(monkeypatch) -> None:
    call_args = {}

    class _DDGS:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def text(self, query, max_results):
            call_args["query"] = query
            call_args["max_results"] = max_results
            return [
                {"title": "a", "href": "https://x", "body": "1"},
                {"title": "b", "href": "https://x", "body": "dup"},
                {"title": "c", "href": "https://y", "body": "2"},
            ]

    fake_mod = types.SimpleNamespace(DDGS=_DDGS)
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)

    rows = web_search_handler("q", num_results=999)
    assert call_args["max_results"] == 20
    assert len(rows) == 2
    assert [r["url"] for r in rows] == ["https://x", "https://y"]
