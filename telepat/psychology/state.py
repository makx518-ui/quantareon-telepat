from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PsychologicalState:
    label: str
    confidence: str
    cues: tuple[str, ...]


_CUES: dict[str, tuple[str, ...]] = {
    "anxious": (
        "тревог", "страшно", "боюсь", "паник", "пережива", "напряж",
        "anxious", "afraid", "worried", "panic",
    ),
    "sad": (
        "груст", "потерял", "потеряла", "одиноко", "больно", "тяжело",
        "sad", "lonely", "loss", "hurts",
    ),
    "angry": (
        "злюсь", "бесит", "раздраж", "ненавиж", "ярость",
        "angry", "furious", "annoyed",
    ),
    "confused": (
        "не понимаю", "запутал", "не знаю что", "сомнева", "выбор",
        "confused", "don't understand", "dont understand", "uncertain",
    ),
    "hopeful": (
        "надеюсь", "получилось", "рад", "рада", "интересно", "хочу попробовать",
        "hopeful", "glad", "excited", "want to try",
    ),
}


def infer_state(message: str) -> PsychologicalState:
    """Detect conversational cues, never a diagnosis.

    A single message is too little evidence for clinical conclusions. This
    function only gives the communication layer a cautious tone hint.
    """
    text = message.lower()
    scores: list[tuple[int, str, tuple[str, ...]]] = []

    for label, markers in _CUES.items():
        found = tuple(marker for marker in markers if marker in text)
        if found:
            scores.append((len(found), label, found))

    if not scores:
        return PsychologicalState(
            label="neutral_or_unknown",
            confidence="low",
            cues=(),
        )

    scores.sort(reverse=True)
    score, label, found = scores[0]
    return PsychologicalState(
        label=label,
        confidence="medium" if score >= 2 else "low",
        cues=found[:4],
    )
