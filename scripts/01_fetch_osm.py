#!/usr/bin/env python3
"""Fetch OpenStreetMap data for the Fornebu/Snarøya area."""

import requests

from config import PROJECT_ROOT

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
    OSM_DIR.mkdir(parents=True, exist_ok=True)

    if output_file.exists():
        print(f"OSM data already exists at {output_file}")
        print("Delete it to re-download.")
        return output_file

    print(f"Fetching OSM data for bbox: {BBOX}")
    print(f"Query: Overpass API...")

    response = requests.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        timeout=180,
    )
    response.raise_for_status()

    output_file.write_bytes(response.content)
    size_mb = len(response.content) / 1024 / 1024
    print(f"Downloaded {size_mb:.1f} MB to {output_file}")
    return output_file


if __name__ == "__main__":
    fetch_osm()
