#!/usr/bin/env python3
"""Fetch OpenStreetMap data for the Fornebu/Snarøya area."""

from pathlib import Path

import requests

from config import PROJECT_ROOT
from utils.provenance import sha256_file, utc_now_iso, write_json

OSM_DIR = PROJECT_ROOT / "network" / "osm"

# Bounding box: Snarøya → E18 area
BBOX = {
    "south": 59.880,
    "west": 10.575,
    "north": 59.910,
    "east": 10.635,
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

OVERPASS_QUERY = f"""
[out:xml][timeout:120];
(
  way["highway"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
  node(w);
  way["railway"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
  node(w);
);
out body;
>;
out skel qt;
"""


def fetch_osm():
    """Download OSM data via Overpass API."""
    output_file = OSM_DIR / "fornebu.osm.xml"
    metadata_file = OSM_DIR / "fornebu.osm.meta.json"
    OSM_DIR.mkdir(parents=True, exist_ok=True)

    if output_file.exists():
        print(f"OSM data already exists at {output_file}")
        print("Delete it to re-download.")
        if not metadata_file.exists():
            write_osm_metadata(output_file, metadata_file, source="existing-file")
        return output_file

    print(f"Fetching OSM data for bbox: {BBOX}")
    print("Query: Overpass API...")

    response = requests.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        timeout=180,
    )
    response.raise_for_status()

    output_file.write_bytes(response.content)
    write_osm_metadata(output_file, metadata_file, source="overpass", status_code=response.status_code)
    size_mb = len(response.content) / 1024 / 1024
    print(f"Downloaded {size_mb:.1f} MB to {output_file}")
    return output_file


def write_osm_metadata(output_file: Path, metadata_file: Path, source: str, status_code: int | None = None) -> None:
    """Write a small metadata receipt for the OSM source snapshot."""
    write_json(
        metadata_file,
        {
            "generated_at": utc_now_iso(),
            "source": source,
            "overpass_url": OVERPASS_URL,
            "status_code": status_code,
            "bbox": BBOX,
            "query": OVERPASS_QUERY.strip(),
            "xml_file": str(output_file),
            "xml_size_bytes": output_file.stat().st_size if output_file.exists() else 0,
            "xml_sha256": sha256_file(output_file),
        },
    )


if __name__ == "__main__":
    fetch_osm()
