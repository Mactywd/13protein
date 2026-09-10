from agents import qa_agents

CHUNKS = [
    {"page_title": "Quality", "url": "https://x/quality", "text": "Standards and audits."},
    {"page_title": "About Us", "url": "https://x/about", "text": "Five plants."},
]


def _fake_stream(captured):
    async def stream(system, user, history=None, model=None):
        captured["system"] = system
        captured["user"] = user
        yield "ok"
    return stream


def test_build_question_message_numbers_context():
    msg = qa_agents.build_question_message("Are you certified?", CHUNKS)
    assert msg.startswith("Question: Are you certified?\n\nContext:\n")
    assert "[1] Quality (https://x/quality)" in msg
    assert "[2] About Us (https://x/about)" in msg


async def test_qa_answer_sends_context_and_slug(monkeypatch):
    captured = {}
    monkeypatch.setattr(qa_agents.llm, "stream", _fake_stream(captured))
    [t async for t in qa_agents.qa_answer("Are you certified?", CHUNKS, "en")]
    assert captured["system"].startswith("# Prompt: qa_answer\n")
    assert "[1] Quality" in captured["user"]


async def test_qa_intro_fills_project_description(monkeypatch):
    captured = {}
    monkeypatch.setattr(qa_agents.llm, "stream", _fake_stream(captured))
    [t async for t in qa_agents.qa_intro("Una whey per palestre", "it")]
    assert "Una whey per palestre" in captured["system"]
    assert "{project_description}" not in captured["system"]


async def test_qa_answer_with_no_chunks_still_calls_model(monkeypatch):
    captured = {}
    monkeypatch.setattr(qa_agents.llm, "stream", _fake_stream(captured))
    [t async for t in qa_agents.qa_answer("Boh?", [], "en")]
    assert captured["user"].endswith("Context:\n")
