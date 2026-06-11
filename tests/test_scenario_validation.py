from pathlib import Path

from scripts.utils.scenario_catalog import production_exports, validate_scenario_catalog, validate_scenario_inputs


def test_production_exports_are_catalog_derived() -> None:
    exports = production_exports()

    assert "scenario_4A_base_morning" in exports
    assert "scenario_4A_v1_afternoon" in exports
    assert "scenario_4A_base_scaled80_morning" not in exports


def test_validate_scenario_inputs_detects_missing_network() -> None:
    errors = validate_scenario_inputs(
        "scenario_bad_morning",
        {
            "family": "scenario_bad",
            "period": "morning",
            "demand": "4A",
            "network": Path("/definitely/missing.net.xml"),
            "routes": "",
            "description": "bad",
            "label": "bad",
            "color": "#000",
            "additional": [],
        },
        check_files=True,
    )

    assert any("missing network" in error for error in errors)
    assert any("no route files" in error for error in errors)


def test_validate_scenario_catalog_shape_without_file_checks() -> None:
    report = validate_scenario_catalog(check_files=False, check_orphans=False)

    assert report["valid"] is True
    assert report["scenario_count"] >= 10
    assert report["export_count"] >= 8
