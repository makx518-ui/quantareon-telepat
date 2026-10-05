from telepat.core.plan import build_plan
from telepat.psychology.service import build_psychology_context
from telepat.psychology.state import infer_state


def test_state_is_a_cue_not_diagnosis() -> None:
    state = infer_state("Мне тревожно и я переживаю из-за этого")
    assert state.label == "anxious"
    assert state.confidence in {"low", "medium"}


def test_full_psychology_has_integrator_boundaries() -> None:
    context = build_psychology_context(
        message="Я чувствую тревогу и не понимаю, что делать",
        language="ru",
        plan=build_plan("personal_reflection"),
    )
    assert "integrator" in context
    assert "psychology" in context["integrator"]


def test_light_context_stays_compact() -> None:
    context = build_psychology_context(
        message="Привет",
        language="ru",
        plan=build_plan("casual_conversation"),
    )
    assert "state_hint" not in context
    assert "communication" in context
