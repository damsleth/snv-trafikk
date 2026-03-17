from scripts.utils.scenario_catalog import PERIODS, SCENARIO_FAMILIES, build_scenarios, declared_demand_variants


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


def test_build_scenarios_supports_scaled_route_variants() -> None:
    scenarios = build_scenarios(
        {
            "scenario_4A_test_scaled": {
                "network": SCENARIO_FAMILIES["scenario_4A_base"]["network"],
                "demand": "4A",
                "demand_scale": 0.8,
                "label": "Testvariant 80 % trafikk",
                "color": "#123456",
                "description": "Scaled demand test",
            },
        }
    )

    morning_scaled = scenarios["scenario_4A_test_scaled_morning"]

    assert morning_scaled["demand"] == "4A"
    assert morning_scaled["demand_scale"] == 0.8
    assert morning_scaled["routes"].endswith("morning_4A_scale_0_8.rou.xml")
    assert morning_scaled["label"] == "Testvariant 80 % trafikk AM"


def test_declared_demand_variants_collect_unique_scales() -> None:
    variants = declared_demand_variants()

    assert ("1A", 1.0) in variants
    assert ("4A", 0.8) in variants
    assert ("4A", 1.0) in variants