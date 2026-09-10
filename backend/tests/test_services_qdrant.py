import pytest
from unittest.mock import patch
from services import qdrant


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _client(captured, result):
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            if "embeddings" in url:
                return _FakeResponse({"data": [{"embedding": [0.1, 0.2]}]})
            captured["json"] = kw["json"]
            captured["url"] = url
            return _FakeResponse({"result": result})

    return FakeClient()


@pytest.mark.asyncio
async def test_search_sends_must_not_filter_when_exclude_docs_given():
    captured = {}
    with patch("services.qdrant.httpx.AsyncClient",
               return_value=_client(captured, [{"payload": {"doc": "quality"}}])):
        out = await qdrant.search("certifications", limit=3, exclude_docs=["home", "about-us"])

    assert out == [{"doc": "quality"}]
    assert captured["json"]["limit"] == 3
    assert captured["json"]["filter"] == {
        "must_not": [{"key": "doc", "match": {"any": ["home", "about-us"]}}]
    }


@pytest.mark.asyncio
async def test_search_omits_filter_when_no_exclude_docs():
    captured = {}
    with patch("services.qdrant.httpx.AsyncClient", return_value=_client(captured, [])):
        await qdrant.search("certifications", limit=3)

    assert "filter" not in captured["json"]


@pytest.mark.asyncio
async def test_search_uses_configured_collection():
    captured = {}
    with patch("services.qdrant.httpx.AsyncClient", return_value=_client(captured, [])):
        await qdrant.search("x")
    assert f"/collections/{qdrant.collection()}/" in captured["url"]


@pytest.mark.asyncio
async def test_search_falls_back_to_keyword_index_on_failure():
    with patch("services.qdrant.httpx.AsyncClient", side_effect=RuntimeError("boom")):
        out = await qdrant.search("certifications", limit=2, exclude_docs=[])
    assert out and out[0]["doc"] == "quality"
