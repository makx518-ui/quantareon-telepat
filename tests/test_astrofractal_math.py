from telepat.astro.engine.micro_cascade import cascade_from_absolute


def test_micro_cascade_is_deterministic() -> None:
    first = cascade_from_absolute(144.322883, levels=7)
    second = cascade_from_absolute(144.322883, levels=7)

    assert first == second
    assert first["sign_name"] == "Лев"
    assert first["sabian"] == 25
    assert len(first["cascade"]) == 7


def test_micro_cascade_stays_in_valid_ranges() -> None:
    result = cascade_from_absolute(359.999, levels=8)

    assert result["sign_index"] == 11
    assert 1 <= result["sabian"] <= 30
    for layer in result["cascade"]:
        assert 0 <= layer["sign_index"] <= 11
        assert 1 <= layer["sabian"] <= 30
