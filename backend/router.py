from typing import Callable
from models import Step
from handlers import intro, project, qa, contact

Handler = Callable

HANDLERS: dict[Step, Handler] = {
    Step.INTRO:           intro.handle,
    Step.PROFILE_SELECT:  intro.handle_profile,
    Step.CATEGORY_SELECT: intro.handle_category,
    Step.FORMAT_SELECT:   intro.handle_format,
    Step.PROJECT_INPUT:   project.handle,
    Step.QA:              qa.handle,
    Step.CONTACT_INPUT:   contact.handle_input,
    Step.CONTACT_CONFIRM: contact.handle_confirm,
    Step.COMPLETED:       contact.handle_completed,
}


def dispatch(step: Step) -> Handler:
    handler = HANDLERS.get(step)
    if handler is None:
        raise ValueError(f"No handler registered for step: {step!r}")
    return handler
