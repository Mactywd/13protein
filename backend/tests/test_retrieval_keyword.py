import json
from services import retrieval_keyword as rk

ROWS = [
    {"id": "quality#0", "doc": "quality", "kind": "page", "page_title": "Quality", "section": "Standards",
     "url": "https://x/quality", "text": "Our plants follow internationally recognized standards and certification.", "status": "publish"},
    {"id": "home#0", "doc": "home", "kind": "page", "page_title": "home", "section": "Hero",
     "url": "https://x/", "text": "Manufacturing excellence for supplement brands.", "status": "publish"},
    {"id": "insights#0", "doc": "insights", "kind": "page", "page_title": "Insights", "section": "x",
     "url": "https://x/insights", "text": "certified certified certified", "status": "draft"},
]


def _index(tmp_path):
    p = tmp_path / "kb.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in ROWS))
    return rk.Index.from_jsonl(p)


def test_search_ranks_by_keyword_and_skips_drafts(tmp_path):
    idx = _index(tmp_path)
    out = idx.search("are you certified", limit=3)
    assert out[0]["doc"] == "quality"
    assert all(r["doc"] != "insights" for r in out)
    assert out[0]["score"] > 0


def test_search_exclude_and_empty(tmp_path):
    idx = _index(tmp_path)
    assert all(r["doc"] != "quality" for r in idx.search("certification", exclude_docs=["quality"]))
    assert idx.search("zzzz qqqq") == []
    assert idx.search("") == []


def test_doc_card(tmp_path):
    idx = _index(tmp_path)
    card = idx.doc_card("quality")
    assert card["title"] == "Quality" and card["url"] == "https://x/quality"
    assert idx.doc_card("nope") is None


def test_format_context():
    text = rk.format_context([ROWS[0]])
    assert text.startswith("[1] Quality (https://x/quality)\n")


def test_real_knowledgebase_has_only_live_chunks():
    from services import retrieval
    # 173 chunk nel bundle, 2 in bozza (insights): l'indice tiene solo i live.
    assert len(retrieval.index().rows) == 171
    assert retrieval.doc_card("protein-powders") is not None
