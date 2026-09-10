from services import usage


def test_record_no_active_accumulator_is_noop():
    # No start() called — record must not raise and current() returns zeros
    usage.record({"cost": 0.01, "prompt_tokens": 5, "completion_tokens": 7})
    assert usage.current().cost == 0.0


def test_start_record_accumulates_then_reset():
    token = usage.start()
    usage.record({"cost": 0.01, "prompt_tokens": 5, "completion_tokens": 7})
    usage.record({"cost": 0.02, "prompt_tokens": 3, "completion_tokens": 1})
    acc = usage.current()
    assert round(acc.cost, 4) == 0.03
    assert acc.prompt_tokens == 8
    assert acc.completion_tokens == 8
    usage.reset(token)
    assert usage.current().cost == 0.0


def test_record_tolerates_missing_keys():
    token = usage.start()
    usage.record({"cost": 0.05})  # no token counts
    acc = usage.current()
    assert acc.cost == 0.05
    assert acc.prompt_tokens == 0
    usage.reset(token)


def test_record_ignores_none_usage():
    token = usage.start()
    usage.record(None)
    assert usage.current().cost == 0.0
    usage.reset(token)


def test_record_tracks_models():
    token = usage.start()
    usage.record({"cost": 0.01, "prompt_tokens": 5, "completion_tokens": 7}, model="google/gemma")
    usage.record({"cost": 0.02}, model="perplexity/sonar")
    usage.record({"cost": 0.0}, model="google/gemma")  # dup collapses
    acc = usage.current()
    assert acc.models == {"google/gemma", "perplexity/sonar"}
    usage.reset(token)


def test_record_model_optional_and_noop_safe():
    # model omitted: still records cost, no model added
    token = usage.start()
    usage.record({"cost": 0.01})
    assert usage.current().models == set()
    usage.reset(token)
    # no active accumulator + model given: must not raise
    usage.record({"cost": 0.01}, model="x")
