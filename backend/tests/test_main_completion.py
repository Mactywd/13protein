from models import ButtonsEvent, CarouselEvent, TextEvent
import main


def test_collect_payload_single_kinds():
    assert main.collect_payload([TextEvent(token="hi")]) is None
    assert main.collect_payload([ButtonsEvent(buttons=[{"label": "A", "value": "a"}])]) == {
        "buttons": [{"label": "A", "value": "a"}]
    }
    assert main.collect_payload([
        CarouselEvent(cards=[{"title": "T", "image": "i", "description": "d", "value": "v"}])
    ]) == {"cards": [{"title": "T", "image": "i", "description": "d", "value": "v"}]}


def test_collect_payload_keeps_both_carousel_and_buttons():
    out = main.collect_payload([
        CarouselEvent(cards=[{"title": "T", "image": "i", "description": "d", "value": "v"}]),
        ButtonsEvent(buttons=[{"label": "A", "value": "a"}]),
    ])
    assert out["cards"] == [{"title": "T", "image": "i", "description": "d", "value": "v"}]
    assert out["buttons"] == [{"label": "A", "value": "a"}]


from models import SessionState


def test_new_topics_returns_only_additions():
    before = {"quality"}
    state = SessionState(topics_cited=["quality", "private-label", "home"])
    assert main.new_topics(before, state) == ["private-label", "home"]


def test_new_topics_empty_when_nothing_added():
    state = SessionState(topics_cited=["quality"])
    assert main.new_topics({"quality"}, state) == []
