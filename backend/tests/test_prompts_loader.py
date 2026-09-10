from agents import prompts


def test_load_returns_file_text():
    assert "13 Protein" in prompts.load("introduction")


def test_load_fills_placeholders():
    text = prompts.load("introduction", default_language="english")
    assert "{default_language}" not in text
    assert "english" in text


def test_unknown_placeholder_left_untouched():
    # Solo le chiavi passate vengono sostituite; le altre restano per dopo.
    text = prompts.load("ask_format", default_language="italian")
    assert "{category}" in text


def test_load_starts_with_slug_line():
    assert prompts.load("introduction", default_language="english").startswith("# Prompt: introduction\n")


def test_load_prepends_shared_header():
    text = prompts.load("introduction", default_language="italian")
    assert text.split("\n", 1)[1].startswith("# Shared Guidelines")


def test_header_mentions_brand_and_no_invention_rule():
    text = prompts.load("introduction", default_language="english")
    assert "13 Protein" in text and "Never invent" in text


def test_header_has_no_em_dash():
    header = prompts.load("introduction", default_language="italian").split("# Role", 1)[0]
    assert "—" not in header
