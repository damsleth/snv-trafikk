#!/usr/bin/env python3
"""Fetch higher-resolution traffic counts from Trafikkdata GraphQL.

The script is intentionally small and configurable because the public GraphQL
schema has changed over time. Use `--query-file` to supply an updated query if
Statens vegvesen changes field names.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import requests

from config import PROJECT_ROOT
from utils.provenance import utc_now_iso, write_json

TRAFIKKDATA_URL = "https://trafikkdata.atlas.vegvesen.no/graphql"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".plans" / "trafikkdata"
DEFAULT_SENSOR_IDS = [
    "17096V443647",
]

DEFAULT_QUERY = """
query TrafficVolume($trafficRegistrationPointIds: [String!]!, $from: DateTime!, $to: DateTime!, $resolution: String!) {
  trafficData(trafficRegistrationPointIds: $trafficRegistrationPointIds, from: $from, to: $to, resolution: $resolution) {
    trafficRegistrationPointId
    name
    from
    to
    lane
    volume
    coverage
  }
}
""".strip()


def read_sensor_ids(path: Path | None, explicit_ids: list[str]) -> list[str]:
    """Resolve sensor ids from CLI and optional text file."""
    sensor_ids = list(explicit_ids)
    if path and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if value and not value.startswith("#"):
                sensor_ids.append(value)
    return sorted(set(sensor_ids or DEFAULT_SENSOR_IDS))


def flatten_rows(data: Any) -> list[dict[str, Any]]:
    """Flatten common Trafikkdata GraphQL response shapes into rows."""
    if isinstance(data, dict):
        if "trafficData" in data and isinstance(data["trafficData"], list):
            return data["trafficData"]
        for value in data.values():
            rows = flatten_rows(value)
            if rows:
                return rows
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return data
    return []


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write flattened rows as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_traffic_data(
    sensor_ids: list[str],
    from_time: str,
    to_time: str,
    resolution: str,
    query: str = DEFAULT_QUERY,
    endpoint: str = TRAFIKKDATA_URL,
) -> dict[str, Any]:
    """Execute the GraphQL request and return decoded JSON."""
    response = requests.post(
        endpoint,
        json={
            "query": query,
            "variables": {
                "trafficRegistrationPointIds": sensor_ids,
                "from": from_time,
                "to": to_time,
                "resolution": resolution,
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Trafikkdata GraphQL traffic counts")
    parser.add_argument("--from", dest="from_time", required=True, help="Start timestamp, e.g. 2026-05-01T00:00:00+02:00")
    parser.add_argument("--to", dest="to_time", required=True, help="End timestamp, e.g. 2026-06-12T00:00:00+02:00")
    parser.add_argument("--resolution", default="PT15M", help="Requested resolution, e.g. PT15M or PASSAGE")
    parser.add_argument("--sensor-id", action="append", default=[], help="Traffic registration point id; may be repeated")
    parser.add_argument("--sensor-file", type=Path, help="Text file with one sensor id per line")
    parser.add_argument("--query-file", type=Path, help="Override GraphQL query file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    sensor_ids = read_sensor_ids(args.sensor_file, args.sensor_id)
    query = args.query_file.read_text(encoding="utf-8") if args.query_file else DEFAULT_QUERY
    payload = fetch_traffic_data(sensor_ids, args.from_time, args.to_time, args.resolution, query=query)
    rows = flatten_rows(payload.get("data", payload))

    safe_resolution = args.resolution.replace(":", "").replace("/", "_")
    output_csv = args.output_dir / f"SNV_{safe_resolution}_{args.from_time[:10]}_{args.to_time[:10]}.csv"
    output_json = output_csv.with_suffix(".raw.json")
    metadata_json = output_csv.with_suffix(".meta.json")

    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if rows:
        write_csv(output_csv, rows)
    write_json(
        metadata_json,
        {
            "generated_at": utc_now_iso(),
            "endpoint": TRAFIKKDATA_URL,
            "from": args.from_time,
            "to": args.to_time,
            "resolution": args.resolution,
            "sensor_ids": sensor_ids,
            "row_count": len(rows),
            "raw_json": str(output_json),
            "csv": str(output_csv) if rows else None,
        },
    )
    print(f"Raw response -> {output_json}")
    if rows:
        print(f"CSV -> {output_csv}")
    print(f"Metadata -> {metadata_json}")


if __name__ == "__main__":
    main()
