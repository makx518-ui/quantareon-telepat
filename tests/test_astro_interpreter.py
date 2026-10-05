import json

from telepat.astro.gemini_interpreter import _parse_summary_payload


def test_parse_current_astro_summary_contract() -> None:
    payload = {
        "overview": "Integrated overview",
        "core_themes": ["theme a", "theme b"],
        "tensions": ["tension a"],
        "resources": ["resource a"],
        "reflection_questions": ["question a"],
    }

    parsed = _parse_summary_payload(json.dumps(payload))

    assert parsed == payload


def test_parse_legacy_astro_summary_labels() -> None:
    payload = {
        "dominant_patterns": ["pattern a", "pattern b"],
        "current_tensions": ["tension a"],
        "resources": ["resource a"],
        "psychological_themes": ["theme a"],
        "questions_to_explore": ["question a"],
    }

    parsed = _parse_summary_payload(json.dumps(payload))

    assert parsed["overview"] == "theme a"
    assert parsed["core_themes"] == ["pattern a", "pattern b"]
    assert parsed["tensions"] == ["tension a"]
    assert parsed["resources"] == ["resource a"]
    assert parsed["reflection_questions"] == ["question a"]
