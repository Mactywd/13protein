import pytest
import router
from models import Step
from handlers import intro, project, qa, contact


def test_every_step_has_a_handler():
    assert set(router.HANDLERS) == set(Step)


def test_dispatch_returns_the_expected_handlers():
    assert router.dispatch(Step.INTRO) is intro.handle
    assert router.dispatch(Step.PROJECT_INPUT) is project.handle
    assert router.dispatch(Step.QA) is qa.handle
    assert router.dispatch(Step.CONTACT_CONFIRM) is contact.handle_confirm


def test_dispatch_raises_on_unknown_step():
    with pytest.raises(ValueError):
        router.dispatch("nope")
