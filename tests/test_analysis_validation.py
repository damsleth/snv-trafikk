import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYZE_PATH = REPO_ROOT / "scripts" / "05_analyze_results.py"


def load_analyze_module():
    spec = importlib.util.spec_from_file_location("analyze_under_test", ANALYZE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyze = load_analyze_module()


def test_generate_validation_report_warns_when_v1_beats_base(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(analyze, "OUTPUT_DIR", tmp_path)
    results = {
        "scenario_4A_base_morning": [{"avg_duration_s": 200, "system_delay_h": 5}],
        "scenario_4A_v1_morning": [{"avg_duration_s": 100, "system_delay_h": 4}],
    }

    report = analyze.generate_validation_report(results)

    assert report["valid"] is False
    assert any("V1 average duration" in warning for warning in report["warnings"])
    assert (tmp_path / "validation_report.json").exists()
