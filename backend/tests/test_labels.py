from lib import labels


def test_profile_buttons_en_it():
    en = labels.buttons("profile", "en")
    it = labels.buttons("profile", "it")
    assert [b["value"] for b in en] == ["product_idea", "new_brand", "supplement_brand", "manufacturing_partner"]
    assert en[0]["label"] == "I have a product idea"
    assert it[0]["label"] == "Ho un'idea di prodotto"


def test_category_and_format_include_not_sure():
    assert labels.buttons("category", "en")[-1]["value"] == labels.NOT_SURE
    assert labels.buttons("format", "en")[-1]["value"] == labels.NOT_SURE
    assert len(labels.buttons("format", "en")) == 8


def test_values_and_label_for():
    assert "proteins" in labels.values("category")
    assert labels.label_for("category", "proteins", "it") == "Proteine"
    assert labels.label_for("category", "unknown", "en") == "unknown"


def test_quote_and_confirm_groups():
    assert labels.values("quote") == [labels.REQUEST_QUOTE]
    assert labels.values("confirm") == [labels.CONFIRM, labels.EDIT]


def test_category_values_cover_retrieval_mapping():
    from services import retrieval
    # ogni categoria tranne "non lo so ancora" deve avere un doc del KB
    mapped = set(retrieval.CATEGORY_DOC)
    assert mapped == set(labels.values("category")) - {labels.NOT_SURE}
