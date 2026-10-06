from analytics.family_master import (
    FamilyMasterError,
    is_panel_valid_for_digit,
    jodi_family_for,
    jodi_family_summary,
    jodis_in_family,
    load_family_master,
    panel_family_for_digit,
    panel_family_for_panel,
    panel_family_summary,
    panel_type_for,
    panels_for_digit,
)


def test_authoritative_master_loads_and_has_expected_counts():
    master = load_family_master()

    assert master["version"] == "1.0.0"
    assert sum(len(values) for values in master["jodi_families"].values()) == 100
    assert sum(
        len(values)
        for family in master["panel_families"].values()
        for values in family.values()
    ) == 220


def test_jodi_family_lookup_preserves_leading_zero():
    assert jodi_family_for("01") == "15"
    assert jodi_family_for("05") == "HALF_RED"
    assert jodi_family_for("00") == "FULL_RED"


def test_jodi_family_members_are_exact():
    assert jodis_in_family("12") == (
        "12", "17", "21", "26", "62", "67", "71", "76"
    )
    assert jodis_in_family("15") == (
        "01", "06", "10", "15", "51", "56", "60", "65"
    )


def test_panel_digit_maps_to_same_numbered_family():
    assert panel_family_for_digit(6) == "6"
    assert panel_family_for_digit("2") == "2"
    assert panel_family_for_digit(0) == "0"


def test_panel_family_lookup_uses_authoritative_membership():
    assert panel_family_for_panel("140") == "5"
    assert panel_family_for_panel("123") == "6"
    assert panel_family_for_panel("000") == "0"


def test_user_example_rejects_cross_family_panel():
    assert is_panel_valid_for_digit("140", 2) is False
    assert is_panel_valid_for_digit("140", 5) is True


def test_valid_family_panel_is_accepted():
    assert is_panel_valid_for_digit("240", 6) is True
    assert is_panel_valid_for_digit("222", 6) is True
    assert is_panel_valid_for_digit("000", 0) is True


def test_panel_type_is_authoritative():
    assert panel_type_for("140") == "single"
    assert panel_type_for("555") == "triple"
    assert panel_type_for("119") == "double"


def test_panels_for_digit_is_family_constrained():
    family_2 = set(panels_for_digit(2))
    assert len(family_2) == 22
    assert "140" not in family_2
    assert "129" in family_2
    assert "444" in family_2


def test_panels_for_digit_can_select_types():
    assert len(panels_for_digit(6, ["single"])) == 12
    assert len(panels_for_digit(6, ["double"])) == 9
    assert len(panels_for_digit(6, ["triple"])) == 1


def test_summaries_match_chart():
    assert jodi_family_summary()["HALF_RED"] == 10
    assert jodi_family_summary()["FULL_RED"] == 10
    assert panel_family_summary()["1"] == {
        "single": 12,
        "double": 9,
        "triple": 1,
    }


def test_invalid_panel_is_rejected():
    try:
        panel_family_for_panel("12")
    except FamilyMasterError:
        pass
    else:
        raise AssertionError("Expected FamilyMasterError")


def test_all_panels_have_one_family_and_type():
    master = load_family_master()
    for family_id, family in master["panel_families"].items():
        for panel_type, panels in family.items():
            for panel in panels:
                assert panel_family_for_panel(panel) == family_id
                assert panel_type_for(panel) == panel_type
