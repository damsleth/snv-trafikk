import importlib.util
from pathlib import Path

from scripts.config import PROJECT_ROOT


REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_SIMULATION_PATH = REPO_ROOT / "scripts" / "04_run_simulation.py"


def load_run_simulation_module():
    spec = importlib.util.spec_from_file_location("run_simulation_config_hygiene", RUN_SIMULATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_simulation = load_run_simulation_module()


def test_validate_config_paths_rejects_old_absolute_root(tmp_path: Path) -> None:
    config_file = tmp_path / "sumo_seed1.cfg"
    config_file.write_text('<net-file value="/Users/damsleth/Code/SNV/network/base/fornebu.net.xml"/>', encoding="utf-8")

    result = run_simulation.validate_config_paths(config_file)

    assert result["valid"] is False
    assert "/Users/damsleth/Code/SNV" in result["offending_markers"]


def test_cleanup_configs_dry_run_lists_only(tmp_path: Path, monkeypatch) -> None:
    scenario_dir = tmp_path / "scenarios" / "scenario_test_morning"
    scenario_dir.mkdir(parents=True)
    config_file = scenario_dir / "sumo_seed1.cfg"
    config_file.write_text("<configuration/>", encoding="utf-8")
    monkeypatch.setattr(run_simulation, "SCENARIOS_DIR", tmp_path / "scenarios")

    targets = run_simulation.cleanup_configs(dry_run=True)

    assert targets == [config_file]
    assert config_file.exists()


def test_create_sumo_config_validation_allows_home_relative_paths(tmp_path: Path, monkeypatch) -> None:
    scenario_name = "scenario_test_morning"
    monkeypatch.setattr(run_simulation, "SCENARIOS_DIR", tmp_path / "scenarios")
    monkeypatch.setitem(
        run_simulation.SCENARIOS,
        scenario_name,
        {
            "network": PROJECT_ROOT / "network" / "base" / "fornebu.net.xml",
            "routes": str(PROJECT_ROOT / "demand" / "routes" / "morning_1A.rou.xml"),
            "additional": [],
        },
    )

    config_file = run_simulation.create_sumo_config(scenario_name, 1)

    assert run_simulation.validate_config_paths(config_file)["valid"] is True
