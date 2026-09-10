from services import llm_mock, usage


def _sys(slug, lang="english"):
    return f"# Prompt: {slug}\n# Language\nWrite in {lang}.\n"


def test_lang_is_read_from_the_language_section_only():
    # Ogni prompt conversazionale ha una sezione `## Italian` fra gli esempi:
    # cercare "italian" in tutto il system prompt rendeva italiana ogni risposta.
    system = _sys("introduction", "english") + "\n# Examples\n\n## Italian\nBenvenuto\n"
    assert llm_mock.lang_of(system) == "en"


def test_real_prompt_in_english_stays_english():
    from agents import prompts
    assert llm_mock.lang_of(prompts.load("introduction", default_language="english")) == "en"
    assert llm_mock.lang_of(prompts.load("introduction", default_language="italian")) == "it"


def test_slug_and_lang():
    assert llm_mock.slug_of(_sys("introduction")) == "introduction"
    assert llm_mock.lang_of(_sys("x", "italian")) == "it"
    assert llm_mock.lang_of(_sys("x")) == "en"
    assert llm_mock.slug_of("no header") is None


async def test_stream_yields_text_and_records_usage():
    token = usage.start()
    try:
        out = "".join([t async for t in llm_mock.stream(_sys("introduction"), "start")])
        acc = usage.current()
    finally:
        usage.reset(token)
    assert "13 Protein" in out
    assert acc.cost > 0 and "mock" in acc.models


async def test_stream_italian_uses_italian_entry():
    out = "".join([t async for t in llm_mock.stream(_sys("introduction", "italian"), "")])
    assert "Benvenuto" in out


async def test_validate_project_rule():
    short = await llm_mock.complete_structured(_sys("validate_project"), "U: A whey protein for gyms")
    assert short["enough"] is False and short["question"]
    long = await llm_mock.complete_structured(
        _sys("validate_project"), "U: A whey protein for gyms\nA: For whom?\nU: Target market Italy, 2 kg tubs")
    assert long["enough"] is True


async def test_extract_contact_rule():
    ok = await llm_mock.complete_structured(_sys("extract_contact"), "Mario Rossi, Rossi Nutrition, mario@example.com")
    assert ok == {"name": "Mario Rossi", "company": "Rossi Nutrition", "email": "mario@example.com", "valid": True}
    bad = await llm_mock.complete_structured(_sys("extract_contact"), "Mario Rossi")
    assert bad["valid"] is False


async def test_qa_answer_cites_context_titles():
    user = "Question: Are you certified?\n\nContext:\n[1] Quality (https://x/quality)\nsome text\n[2] About Us (https://x/about)\n"
    out = "".join([t async for t in llm_mock.stream(_sys("qa_answer"), user)])
    assert "Quality" in out and "About Us" in out


async def test_confirm_lead_renders_bullets_from_input():
    system = _sys("confirm_lead") + '# Input\nLead:\n{"profile": "new_brand", "quoteRequested": true}\n'
    out = "".join([t async for t in llm_mock.stream(system, "")])
    assert "new_brand" in out


async def test_unknown_slug_falls_back():
    out = await llm_mock.complete(_sys("does_not_exist"), "x")
    assert out.startswith("[mock:does_not_exist]")
