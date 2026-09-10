import json
from models import TextEvent, ButtonsEvent, CarouselEvent, ErrorEvent, DoneEvent
from stream import format_sse


def test_text_event_format():
    result = format_sse(TextEvent(token="ciao")).decode()
    assert result == 'event: text\ndata: {"token": "ciao"}\n\n'


def test_buttons_event_format():
    buttons = [{"label": "Proteins", "value": "proteins"}]
    result = format_sse(ButtonsEvent(buttons=buttons)).decode()
    lines = result.strip().split("\n")
    assert lines[0] == "event: buttons"
    data = json.loads(lines[1].removeprefix("data: "))
    assert data["buttons"][0]["value"] == "proteins"


def test_carousel_event_format():
    cards = [{"title": "Protein Powders", "image": "", "description": "d", "value": "doc:protein-powders"}]
    result = format_sse(CarouselEvent(cards=cards)).decode()
    assert "event: carousel" in result
    data = json.loads(result.split("data: ")[1])
    assert data["cards"][0]["title"] == "Protein Powders"


def test_error_event_format():
    result = format_sse(ErrorEvent(message="ops")).decode()
    assert "event: error" in result
    data = json.loads(result.split("data: ")[1])
    assert data["message"] == "ops"


def test_done_event_format():
    result = format_sse(DoneEvent(step="qa")).decode()
    assert "event: done" in result
    data = json.loads(result.split("data: ")[1])
    assert data["step"] == "qa"


def test_event_ends_with_double_newline():
    result = format_sse(TextEvent(token="x")).decode()
    assert result.endswith("\n\n")


def test_done_event_serializes_input_enabled():
    from models import DoneEvent
    from stream import format_sse
    out = format_sse(DoneEvent(step="category_select", input_enabled=False)).decode()
    assert "event: done" in out
    assert '"input_enabled": false' in out


def test_done_event_defaults_input_enabled_true():
    from models import DoneEvent
    from stream import format_sse
    out = format_sse(DoneEvent(step="project_input")).decode()
    assert '"input_enabled": true' in out


def test_message_break_event_format():
    from models import MessageBreakEvent
    result = format_sse(MessageBreakEvent()).decode()
    assert result == "event: message_break\ndata: {}\n\n"


def test_lead_info_event_format():
    import json
    from models import LeadInfoEvent
    out = format_sse(LeadInfoEvent(info={"profile": "new_brand"})).decode()
    assert out.startswith("event: lead_info")
    assert json.loads(out.split("data: ")[1])["info"]["profile"] == "new_brand"
