import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SERVE_PATH = REPO_ROOT / "scripts" / "08_serve_presentation.py"


def load_serve_module():
	spec = importlib.util.spec_from_file_location("serve_presentation_under_test", SERVE_PATH)
	assert spec is not None
	assert spec.loader is not None
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


serve_presentation = load_serve_module()


def test_validate_patched_run_payload_accepts_minimal_payload() -> None:
	serve_presentation.validate_patched_run_payload({"package": {}, "period": "morning", "seed": 1})


def test_validate_patched_run_payload_rejects_bad_period() -> None:
	with pytest.raises(ValueError, match="period"):
		serve_presentation.validate_patched_run_payload({"package": {}, "period": "night"})


def test_validate_patched_run_payload_rejects_large_seed() -> None:
	with pytest.raises(ValueError, match="seed"):
		serve_presentation.validate_patched_run_payload({"package": {}, "seed": 101})
