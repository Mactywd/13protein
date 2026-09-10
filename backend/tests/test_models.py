from models import SessionState, Step


def test_defaults():
    s = SessionState()
    assert s.current_step == Step.INTRO
    assert s.default_language == "en"
    assert s.profile is None and s.quote_requested is False


def test_to_lead_info_shape():
    s = SessionState(profile="product_idea", category="proteins", format="powders",
                     project_description="Whey for gyms", questions_asked=["Certified?"],
                     topics_cited=["quality"], quote_requested=True,
                     contact={"name": "Mario", "company": "Rossi", "email": "m@example.com"})
    info = s.to_lead_info()
    assert info["profile"] == "product_idea"
    assert info["projectDescription"] == "Whey for gyms"
    assert info["topicsCited"] == ["quality"]
    assert info["contact"]["email"] == "m@example.com"
    assert info["language"] == "en"


def test_to_lead_info_placeholders_when_empty():
    info = SessionState().to_lead_info()
    assert info["profile"] is None
    assert info["contact"] == {"name": None, "company": None, "email": None}
    assert info["questionsAsked"] == []


def test_state_roundtrip_json():
    s = SessionState(profile="new_brand", topics_cited=["home"])
    assert SessionState.model_validate_json(s.model_dump_json()) == s
