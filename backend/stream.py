import json
from models import (Event, TextEvent, ButtonsEvent, CarouselEvent, ErrorEvent,
                    LeadInfoEvent, DoneEvent, MessageBreakEvent)


def format_sse(event: Event) -> bytes:
    if isinstance(event, TextEvent):
        data = json.dumps({"token": event.token})
        name = "text"
    elif isinstance(event, ButtonsEvent):
        data = json.dumps({"buttons": event.buttons})
        name = "buttons"
    elif isinstance(event, CarouselEvent):
        data = json.dumps({"cards": event.cards})
        name = "carousel"
    elif isinstance(event, ErrorEvent):
        data = json.dumps({"message": event.message})
        name = "error"
    elif isinstance(event, LeadInfoEvent):
        data = json.dumps({"info": event.info})
        name = "lead_info"
    elif isinstance(event, DoneEvent):
        data = json.dumps({"step": event.step, "input_enabled": event.input_enabled})
        name = "done"
    elif isinstance(event, MessageBreakEvent):
        data = "{}"
        name = "message_break"
    else:
        raise ValueError(f"Unknown event type: {type(event)}")
    return f"event: {name}\ndata: {data}\n\n".encode()
