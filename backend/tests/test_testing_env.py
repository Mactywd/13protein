import json
import testing_env


def test_merge_replaces_only_sentinel_fields():
    current = {
        "profile": "new_brand",                                       # risposto -> tenuto
        "category": None,                                             # sentinella -> sostituito
        "format": None,                                               # sentinella -> sostituito
        "projectDescription": "Una linea pre-workout",                # risposto -> tenuto
        "questionsAsked": [],                                         # sentinella -> sostituito
        "topicsCited": ["quality"],                                   # risposto -> tenuto
        "quoteRequested": False,                                      # sentinella -> sostituito
        "contact": {"name": None, "company": None, "email": None},    # sentinella -> sostituito
        "language": "it",
    }
    facsimile = {
        "profile": "product_idea",
        "category": "proteins",
        "format": "powders",
        "projectDescription": "Facsimile",
        "questionsAsked": ["Are you certified?"],
        "topicsCited": ["about-us"],
        "quoteRequested": True,
        "contact": {"name": "Mario", "company": "Rossi", "email": "m@x.it"},
    }

    merged = testing_env.merge_with_facsimile(current, facsimile)

    assert merged["profile"] == "new_brand"
    assert merged["category"] == "proteins"
    assert merged["format"] == "powders"
    assert merged["projectDescription"] == "Una linea pre-workout"
    assert merged["questionsAsked"] == ["Are you certified?"]
    assert merged["topicsCited"] == ["quality"]
    assert merged["quoteRequested"] is True
    assert merged["contact"]["email"] == "m@x.it"
    assert merged["language"] == "it"


def test_merge_keeps_partial_lists_untouched():
    current = {"questionsAsked": ["Solo una"]}
    facsimile = {"questionsAsked": ["A", "B"]}
    assert testing_env.merge_with_facsimile(current, facsimile)["questionsAsked"] == ["Solo una"]


def test_load_facsimile_defaults_to_product_idea(tmp_path, monkeypatch):
    data = {"product_idea": {"profile": "P"}, "new_brand": {"profile": "N"}}
    fixture = tmp_path / "testing_facsimiles.json"
    fixture.write_text(json.dumps(data))
    monkeypatch.setattr(testing_env, "FACSIMILES_PATH", fixture)

    assert testing_env.load_facsimile(None)["profile"] == "P"
    assert testing_env.load_facsimile("sconosciuto")["profile"] == "P"
    assert testing_env.load_facsimile("new_brand")["profile"] == "N"


def test_shipped_facsimiles_cover_every_profile():
    from lib import labels
    with testing_env.FACSIMILES_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    assert set(data) == set(labels.values("profile"))
    for value in data.values():
        assert set(testing_env.FIELD_SENTINELS) <= set(value)
