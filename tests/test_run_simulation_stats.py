import importlib.util
import os
from pathlib import Path

import pytest

from scripts.config import PROJECT_ROOT, SNV_ROOT_ENV, sumo_config_path


REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_SIMULATION_PATH = REPO_ROOT / "scripts" / "04_run_simulation.py"


def load_run_simulation_module():
    spec = importlib.util.spec_from_file_location("run_simulation_under_test", RUN_SIMULATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_simulation = load_run_simulation_module()


def test_sumo_config_path_uses_home_relative_form() -> None:
  formatted = sumo_config_path(PROJECT_ROOT / "output" / "scenario" / "seed_1" / "tripinfo.xml")

  assert os.environ[SNV_ROOT_ENV] == str(PROJECT_ROOT)
  assert formatted == "~/code/snv-trafikk/output/scenario/seed_1/tripinfo.xml"


def test_create_sumo_config_writes_home_relative_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  scenario_name = "scenario_test_morning"
  monkeypatch.setattr(run_simulation, "OUTPUT_DIR", PROJECT_ROOT / "output")
  monkeypatch.setattr(run_simulation, "SCENARIOS_DIR", tmp_path / "scenarios")
  monkeypatch.setitem(
    run_simulation.SCENARIOS,
    scenario_name,
    {
      "network": PROJECT_ROOT / "network" / "base" / "fornebu.net.xml",
      "routes": str(PROJECT_ROOT / "demand" / "routes" / "morning_1A.rou.xml"),
      "additional": [str(PROJECT_ROOT / "network" / "signals" / "roundabout_params.add.xml")],
    },
  )

  config_file = run_simulation.create_sumo_config(scenario_name, seed=3)

  config_text = config_file.read_text(encoding="utf-8")
  assert 'value="~/code/snv-trafikk/network/base/fornebu.net.xml"' in config_text
  assert 'value="~/code/snv-trafikk/demand/routes/morning_1A.rou.xml"' in config_text
  assert 'value="~/code/snv-trafikk/output/scenario_test_morning/seed_3/tripinfo.xml"' in config_text
  assert str(PROJECT_ROOT) not in config_text


def test_parse_stats_extracts_shared_kpis(tmp_path: Path) -> None:
    output_dir = tmp_path / "scenario" / "seed_1"
    output_dir.mkdir(parents=True)

    (output_dir / "tripinfo.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<routes>
  <tripinfo id="veh_0" depart="0.0" arrival="100.0" departLane="-27195187#3_0" arrivalLane="edge_out_0" duration="100.0" waitingTime="10.0" timeLoss="20.0" />
  <tripinfo id="veh_1" depart="5.0" arrival="205.0" departLane="other_edge_0" arrivalLane="27195187#2_0" duration="200.0" waitingTime="20.0" timeLoss="40.0" />
  <tripinfo id="emer_2" depart="10.0" arrival="70.0" departLane="emergency_edge_0" arrivalLane="emergency_out_0" duration="60.0" timeLoss="5.0" />
</routes>
""",
        encoding="utf-8",
    )

    (output_dir / "summary.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<summary>
  <step time="0" waiting="10" halting="5" />
  <step time="1" waiting="30" halting="7" />
</summary>
""",
        encoding="utf-8",
    )

    (output_dir / "stats.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<statistics>
  <vehicles loaded="250" inserted="130" waiting="120" teleports="1" />
  <vehicleTripStatistics duration="150.0" waitingTime="15.0" timeLoss="30.0" speed="10.0" />
</statistics>
""",
        encoding="utf-8",
    )

    stats = run_simulation.parse_stats(output_dir)

    assert stats["completed_vehicles"] == 2
    assert stats["avg_duration_s"] == pytest.approx(150.0)
    assert stats["max_duration_s"] == pytest.approx(200.0)
    assert stats["avg_waiting_time_s"] == pytest.approx(15.0)
    assert stats["avg_time_loss_s"] == pytest.approx(30.0)
    assert stats["completed_time_loss_h"] == pytest.approx(60.0 / 3600.0)

    assert stats["emergency_count"] == 1
    assert stats["emergency_avg_duration_s"] == pytest.approx(60.0)
    assert stats["emergency_max_duration_s"] == pytest.approx(60.0)
    assert stats["emergency_avg_time_loss_s"] == pytest.approx(5.0)

    assert stats["snaroya_origin_count"] == 1
    assert stats["snaroya_avg_duration_s"] == pytest.approx(100.0)
    assert stats["snaroya_avg_time_loss_s"] == pytest.approx(20.0)

    assert stats["blocked_vehicle_h"] == pytest.approx(40.0 / 3600.0)
    assert stats["queued_vehicle_h"] == pytest.approx(52.0 / 3600.0)
    assert stats["peak_waiting"] == 30
    assert stats["peak_queue_proxy"] == 37

    assert stats["loaded"] == 250
    assert stats["inserted"] == 130
    assert stats["waiting"] == 120
    assert stats["teleports"] == 1
    assert stats["not_inserted"] == 120
    assert stats["system_delay_h"] == pytest.approx(100.0 / 3600.0)
    assert stats["queue_length_km"] == pytest.approx(0.6)


def test_parse_stats_ignores_malformed_tripinfo_but_keeps_other_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "scenario" / "seed_1"
    output_dir.mkdir(parents=True)

    (output_dir / "tripinfo.xml").write_text("<routes><tripinfo>", encoding="utf-8")
    (output_dir / "stats.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<statistics>
  <vehicles loaded="10" inserted="8" waiting="2" teleports="0" />
</statistics>
""",
        encoding="utf-8",
    )

    stats = run_simulation.parse_stats(output_dir)

    assert stats["loaded"] == 10
    assert stats["inserted"] == 8
    assert stats["not_inserted"] == 2
    assert stats["queue_length_km"] == pytest.approx(0.0)