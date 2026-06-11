import json
from pathlib import Path

from scripts.utils.provenance import sha256_file, utc_now_iso, write_json


def test_sha256_file_returns_digest(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("snv\n", encoding="utf-8")

    assert sha256_file(sample) == "7d6165a3365de389b63e916459e386f8d3ed256c8dce4e41ed65a1b9fb295653"


def test_write_json_is_stable_and_utf8(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "meta.json"

    write_json(out, {"b": 2, "a": "å"})

    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == {"a": "å", "b": 2}


def test_utc_now_iso_is_utc() -> None:
    assert utc_now_iso().endswith("+00:00")
