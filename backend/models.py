from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field


class Step(str, Enum):
    INTRO = "intro"
    PROFILE_SELECT = "profile_select"
    CATEGORY_SELECT = "category_select"
    FORMAT_SELECT = "format_select"
    PROJECT_INPUT = "project_input"
    QA = "qa"
    CONTACT_INPUT = "contact_input"
    CONTACT_CONFIRM = "contact_confirm"
    COMPLETED = "completed"


class SessionState(BaseModel):
    current_step: Step = Step.INTRO
    default_language: str = "en"

    # qualificazione (slug del form del sito, vedi lib/labels.py)
    profile: str | None = None
    category: str | None = None
    format: str | None = None

    # progetto
    project_raw: str = ""                 # transcript U:/A: dello step progetto
    project_description: str | None = None
    followup_count: int = 0

    # domande libere
    questions_asked: list[str] = Field(default_factory=list)
    topics_cited: list[str] = Field(default_factory=list)   # doc del KB citati
    quote_requested: bool = False

    # contatto e output
    contact: dict | None = None           # {name, company, email}
    lead_info: dict | None = None

    # carry-forward dei costi di un turno senza bolle visibili (main.py::chat)
    pending_cost: float = 0.0
    pending_prompt_tokens: int = 0
    pending_completion_tokens: int = 0
    pending_models: list[str] = Field(default_factory=list)

    def to_lead_info(self) -> dict:
        contact = self.contact or {}
        return {
            "profile": self.profile,
            "category": self.category,
            "format": self.format,
            "projectDescription": self.project_description,
            "questionsAsked": list(self.questions_asked),
            "topicsCited": list(self.topics_cited),
            "quoteRequested": self.quote_requested,
            "contact": {
                "name": contact.get("name"),
                "company": contact.get("company"),
                "email": contact.get("email"),
            },
            "language": self.default_language,
        }


@dataclass
class TextEvent:
    token: str


@dataclass
class ButtonsEvent:
    buttons: list[dict]  # [{"label": str, "value": str}]


@dataclass
class CarouselEvent:
    cards: list[dict]  # [{"title", "image", "description", "value"}]


@dataclass
class ErrorEvent:
    message: str


@dataclass
class LeadInfoEvent:
    info: dict


@dataclass
class DoneEvent:
    step: str
    input_enabled: bool = True


# Separatore inserito nel transcript a un MessageBreakEvent (chats.messages_from_row
# lo usa per ri-espandere un turno in più bolle, come nel client).
MESSAGE_BREAK = "\x1e"


@dataclass
class MessageBreakEvent:
    """Chiude la bolla corrente senza chiudere il turno."""


Event = (TextEvent | ButtonsEvent | CarouselEvent | ErrorEvent | LeadInfoEvent
         | DoneEvent | MessageBreakEvent)
