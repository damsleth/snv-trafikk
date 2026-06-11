import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORT_PATH = REPO_ROOT / "scripts" / "07_export_presentation_data.py"


def load_export_module():
    spec = importlib.util.spec_from_file_location("export_presentation_under_test", EXPORT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


export = load_export_module()


def test_selected_export_scenarios_come_from_catalog() -> None:
    scenarios = export.selected_export_scenarios()

    assert "scenario_4A_base_morning" in scenarios
    assert "scenario_4A_base_scaled80_morning" not in scenarios


def test_select_seed_seed_1_requires_complete_files(tmp_path: Path, monkeypatch) -> None:
    scenario = "scenario_demo_morning"
    seed_dir = tmp_path / scenario / "seed_1"
    seed_dir.mkdir(parents=True)
    (seed_dir / "tripinfo.xml").write_text("<routes/>", encoding="utf-8")
    (seed_dir / "summary.xml").write_text("<summary/>", encoding="utf-8")
    monkeypatch.setattr(export, "OUTPUT_DIR", tmp_path)

    assert export.select_seed(scenario, "seed_1") is None

    (seed_dir / "fcd.xml").write_text("<fcd-export/>", encoding="utf-8")
    assert export.select_seed(scenario, "seed_1") == 1


def test_validate_export_inputs_reports_missing_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(export, "OUTPUT_DIR", tmp_path)

    result = export.validate_export_inputs("missing_scenario", 1)

    assert result["valid"] is False
    assert result["has_tripinfo"] is False
