from scripts.utils.scenario_catalog import PERIODS, SCENARIO_FAMILIES, build_scenarios


def test_build_scenarios_expands_all_allowed_periods() -> None:
    scenarios = build_scenarios()
    expected_count = sum(len(family.get("periods", list(PERIODS.keys()))) for family in SCENARIO_FAMILIES.values())

    assert len(scenarios) == expected_count
    assert "scenario_4A_base_morning" in scenarios
    assert "scenario_4A_base_afternoon" in scenarios
    assert "scenario_4A_base_event_afternoon" in scenarios
    assert "scenario_4A_base_event_morning" not in scenarios


def test_build_scenarios_populates_required_metadata() -> None:
    scenarios = build_scenarios()

    morning_base = scenarios["scenario_4A_base_morning"]
    afternoon_event = scenarios["scenario_4A_base_event_afternoon"]

    assert morning_base["family"] == "scenario_4A_base"
    assert morning_base["period"] == "morning"
    assert morning_base["label"] == "Base (dagens profil) AM"
    assert morning_base["description"].endswith("(morning)")
    assert any(path.endswith("roundabout_params.add.xml") for path in morning_base["additional"])
    assert morning_base["routes"].endswith("morning_4A.rou.xml")

    assert afternoon_event["period"] == "afternoon"
    assert "event_overlay.rou.xml" in afternoon_event["routes"]
    assert afternoon_event["label"] == "Base + konsert PM"