from telepat.core.plan import build_plan


def test_astro_plan_uses_astro_and_memory() -> None:
    plan = build_plan("astropsychology")
    assert plan.use_astro is True
    assert plan.use_memory is True
    assert plan.psychology_level == "full"
    assert plan.avatar_state == "thinking"


def test_casual_plan_avoids_unnecessary_astro() -> None:
    plan = build_plan("casual_conversation")
    assert plan.use_astro is False
    assert plan.psychology_level == "light"
    assert plan.avatar_state == "idle"


def test_explicit_memory_plan_is_deep_memory_without_astro() -> None:
    plan = build_plan("factual_user_memory")
    assert plan.use_memory is True
    assert plan.use_astro is False
    assert plan.response_mode == "memory"
