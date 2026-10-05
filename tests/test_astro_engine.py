from telepat.astro.engine import kod360, micro_cascade


def test_kod360_is_complete() -> None:
    data = kod360.load()
    assert len(data) == 360


def test_micro_cascade_is_deterministic() -> None:
    result = micro_cascade.cascade_from_absolute(144.322883, levels=4)
    assert result["sign_name"] == "Лев"
    assert result["sabian"] == 25
    assert len(result["cascade"]) == 4
    assert all("sign_name" in level for level in result["cascade"])
