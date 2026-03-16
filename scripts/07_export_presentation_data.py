#!/usr/bin/env python3
"""Export SUMO results to a presentation-friendly web package."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import sumolib

import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
PRESENTATION_DIR = PROJECT_ROOT / "web" / "presentation"
DATA_DIR = PRESENTATION_DIR / "data"
NETWORKS_DIR = DATA_DIR / "networks"
PLAYBACK_DIR = DATA_DIR / "playback"
SUMMARY_FILE = OUTPUT_DIR / "report" / "summary_stats.json"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from utils.scenario_catalog import SCENARIOS, scenario_family, scenario_label, scenario_period


SCENARIOS_TO_EXPORT = [
    "scenario_4A_base_morning",
    "scenario_4A_base_afternoon",
    "scenario_4A_v1_morning",
    "scenario_4A_v1_afternoon",
    "scenario_4A_v2_morning",
    "scenario_4A_v2_afternoon",
    "scenario_4A_v3_morning",
    "scenario_4A_v3_afternoon",
    "scenario_4A_v1_rolfsbukt_morning",
    "scenario_4A_v1_rolfsbukt_afternoon",
    "scenario_4A_base_event_afternoon",
    "scenario_4A_v1_event_afternoon",
]

PEDESTRIAN_PULSE_PERIOD_S = 450
PLAYBACK_INTERVAL_S = 15


def stats_value(stats: dict, key: str, default: float = 0.0) -> float:
    if f"{key}_mean" in stats:
        return float(stats[f"{key}_mean"])
    if key in stats:
        return float(stats[key])
    return default


def load_summary_stats() -> dict:
    if not SUMMARY_FILE.exists():
        return {}
    return json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))


def load_scenario_stats(scenario_name: str, summary_stats: dict) -> dict:
    if scenario_name in summary_stats:
        return summary_stats[scenario_name]
    run_stats = OUTPUT_DIR / scenario_name / "seed_1" / "run_stats.json"
    if run_stats.exists():
        return json.loads(run_stats.read_text(encoding="utf-8"))
    return {}


def lonlat(net: sumolib.net.Net, x: float, y: float) -> list[float]:
    lon, lat = net.convertXY2LonLat(x, y)
    return [lon, lat]


def midpoint(shape: list[tuple[float, float]]) -> tuple[float, float]:
    if not shape:
        return (0.0, 0.0)
    return shape[len(shape) // 2]


def export_network_geojson(network_path: Path, family_name: str) -> dict:
    net = sumolib.net.readNet(str(network_path))
    features = []

    for edge in net.getEdges():
        if edge.getFunction() == "internal":
            continue
        if not edge.getLanes():
            continue
        drivable = any(
            lane.allows("passenger") or lane.allows("bus") or lane.allows("emergency")
            for lane in edge.getLanes()
        )
        if not drivable:
            continue

        shape = edge.getShape()
        if len(shape) < 2:
            continue

        coords = [lonlat(net, x, y) for x, y in shape]
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
                "properties": {
                    "id": edge.getID(),
                    "name": edge.getName() or edge.getID(),
                    "lanes": edge.getLaneNumber(),
                    "speed_kmh": round(edge.getSpeed() * 3.6, 1),
                },
            }
        )

    bbox_xy = net.getBBoxXY()
    west_south = lonlat(net, *bbox_xy[0])
    east_north = lonlat(net, *bbox_xy[1])
    bounds = [
        [west_south[1], west_south[0]],
        [east_north[1], east_north[0]],
    ]
    center = [
        (bounds[0][0] + bounds[1][0]) / 2,
        (bounds[0][1] + bounds[1][1]) / 2,
    ]

    out_path = NETWORKS_DIR / f"{family_name}.geojson"
    out_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": features,
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    bus_route_edges = ["313965530#1", "53141119", "27184811#3", "515410724#0"]
    bus_route = []
    for edge_id in bus_route_edges:
        edge = net.getEdge(edge_id)
        x, y = midpoint(edge.getShape())
        lon, lat = net.convertXY2LonLat(x, y)
        bus_route.append([lat, lon])

    hotspots = []
    hotspot_specs = [
        ("flytarnet", "Flytårnet stasjon", "53141119"),
        ("rolfsbukt", "Rolfsbuktveien", "27184811#3"),
        ("nordre_rundkjoring", "Nordre rundkjøring", "313965530#1"),
    ]
    for hotspot_id, label, edge_id in hotspot_specs:
        edge = net.getEdge(edge_id)
        x, y = midpoint(edge.getShape())
        lon, lat = net.convertXY2LonLat(x, y)
        hotspots.append({"id": hotspot_id, "label": label, "lat": lat, "lon": lon})

    return {
        "file": f"data/networks/{family_name}.geojson",
        "center": center,
        "bounds": bounds,
        "bus_route": bus_route,
        "pedestrian_hotspots": hotspots,
    }


def export_playback(scenario_name: str, scenario_def: dict) -> dict | None:
    fcd_path = OUTPUT_DIR / scenario_name / "seed_1" / "fcd.xml"
    if not fcd_path.exists():
        return None

    net = sumolib.net.readNet(str(scenario_def["network"]))
    frames = []
    max_edge_count = 0
    max_event_count = 0

    context = ET.iterparse(str(fcd_path), events=("end",))
    for _, elem in context:
        if elem.tag != "timestep":
            continue

        time_s = int(round(float(elem.get("time", "0"))))
        if time_s % PLAYBACK_INTERVAL_S != 0:
            elem.clear()
            continue

        edge_stats: dict[str, list[float]] = defaultdict(lambda: [0, 0.0, 0, 0])
        emergency_positions = []

        for vehicle in elem.findall("vehicle"):
            lane_id = vehicle.get("lane", "")
            edge_id = lane_id.rsplit("_", 1)[0] if "_" in lane_id else lane_id
            speed = float(vehicle.get("speed", "0"))
            vehicle_id = vehicle.get("id", "")
            vehicle_type = vehicle.get("type", "car")

            row = edge_stats[edge_id]
            row[0] += 1
            row[1] += speed

            if vehicle_type == "emergency" or vehicle_id.startswith("emer_"):
                row[2] += 1
                lon, lat = net.convertXY2LonLat(float(vehicle.get("x", "0")), float(vehicle.get("y", "0")))
                emergency_positions.append(
                    {
                        "id": vehicle_id,
                        "lat": lat,
                        "lon": lon,
                        "speed": round(speed * 3.6, 1),
                    }
                )

            if vehicle_type == "event_car" or vehicle_id.startswith("event_"):
                row[3] += 1

        edge_payload = {}
        for edge_id, values in edge_stats.items():
            count, speed_sum, emergency_count, event_count = values
            avg_speed_kmh = round((speed_sum / count) * 3.6, 1) if count else 0.0
            edge_payload[edge_id] = [int(count), avg_speed_kmh, int(emergency_count), int(event_count)]
            max_edge_count = max(max_edge_count, int(count))
            max_event_count = max(max_event_count, int(event_count))

        frames.append({"t": time_s, "edges": edge_payload, "emergency": emergency_positions})
        elem.clear()

    out_path = PLAYBACK_DIR / f"{scenario_name}.json"
    out_path.write_text(
        json.dumps(
            {
                "interval_s": PLAYBACK_INTERVAL_S,
                "frames": frames,
                "max_edge_count": max_edge_count,
                "max_event_count": max_event_count,
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    return {
        "file": f"data/playback/{scenario_name}.json",
        "frame_count": len(frames),
        "interval_s": PLAYBACK_INTERVAL_S,
    }


def build_kpis(stats: dict) -> dict:
    return {
        "avg_duration_min": round(stats_value(stats, "avg_duration_s") / 60.0, 1),
        "system_delay_h": round(stats_value(stats, "system_delay_h"), 1),
        "queue_km": round(stats_value(stats, "queue_length_km"), 1),
        "blocked_vehicles": round(stats_value(stats, "not_inserted")),
        "peak_waiting": round(stats_value(stats, "peak_waiting")),
        "emergency_avg_min": round(stats_value(stats, "emergency_avg_duration_s") / 60.0, 1),
        "snaroya_avg_min": round(stats_value(stats, "snaroya_avg_duration_s") / 60.0, 1),
    }


def network_family_id(family_name: str) -> str:
    if family_name.endswith("_event"):
        return family_name[:-6]
    return family_name


def build_manifest() -> dict:
    summary_stats = load_summary_stats()
    available_scenarios = [name for name in SCENARIOS_TO_EXPORT if name in SCENARIOS]
    family_ids = sorted({network_family_id(scenario_family(name)) for name in available_scenarios})

    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    PLAYBACK_DIR.mkdir(parents=True, exist_ok=True)

    networks = {}
    for family_name in family_ids:
        networks[family_name] = export_network_geojson(Path(SCENARIOS[f"{family_name}_morning"]["network"]), family_name)

    scenarios = {}
    for scenario_name in available_scenarios:
        stats = load_scenario_stats(scenario_name, summary_stats)
        playback = export_playback(scenario_name, SCENARIOS[scenario_name])
        if not playback:
            continue

        scenarios[scenario_name] = {
            "family": scenario_family(scenario_name),
            "period": scenario_period(scenario_name),
            "label": scenario_label(scenario_name),
            "network": network_family_id(scenario_family(scenario_name)),
            "playback": playback,
            "kpis": build_kpis(stats),
            "has_event_overlay": "event" in scenario_name,
            "source": "sumo_seed1",
        }

    event_base = scenarios.get("scenario_4A_base_event_afternoon", {}).get("kpis", {})
    event_regular = scenarios.get("scenario_4A_base_afternoon", {}).get("kpis", {})
    event_v1 = scenarios.get("scenario_4A_v1_event_afternoon", {}).get("kpis", {})
    event_v1_regular = scenarios.get("scenario_4A_v1_afternoon", {}).get("kpis", {})

    def ratio(a: dict, b: dict, key: str, fallback: float = 1.0) -> float:
        bval = b.get(key, 0)
        if not bval:
            return fallback
        return round(a.get(key, bval) / bval, 2)

    event_multipliers = {
        "base": {
            "avg_duration": ratio(event_base, event_regular, "avg_duration_min"),
            "system_delay": ratio(event_base, event_regular, "system_delay_h"),
            "queue": ratio(event_base, event_regular, "queue_km"),
            "emergency": ratio(event_base, event_regular, "emergency_avg_min"),
        },
        "v1": {
            "avg_duration": ratio(event_v1, event_v1_regular, "avg_duration_min"),
            "system_delay": ratio(event_v1, event_v1_regular, "system_delay_h"),
            "queue": ratio(event_v1, event_v1_regular, "queue_km"),
            "emergency": ratio(event_v1, event_v1_regular, "emergency_avg_min"),
        },
    }

    default_network = networks.get("scenario_4A_base", {})
    return {
        "generated_from": "scripts/07_export_presentation_data.py",
        "default_center": default_network.get("center", [59.9, 10.61]),
        "default_bounds": default_network.get("bounds", [[59.88, 10.57], [59.92, 10.66]]),
        "networks": networks,
        "scenarios": scenarios,
        "families": [
            {"id": "scenario_4A_base", "label": "Base (dagens profil)"},
            {"id": "scenario_4A_v1", "label": "V1"},
            {"id": "scenario_4A_v2", "label": "V2"},
            {"id": "scenario_4A_v3", "label": "V3"},
            {"id": "scenario_4A_v1_rolfsbukt", "label": "V1 + miljøgate"},
        ],
        "synthetic": {
            "midday_factor": {
                "edge_load": 0.58,
                "avg_duration": 0.82,
                "system_delay": 0.62,
                "queue": 0.55,
                "emergency": 0.9,
            },
            "event_multipliers": event_multipliers,
            "fallback_event_multipliers": {
                "avg_duration": round((event_multipliers["base"]["avg_duration"] + event_multipliers["v1"]["avg_duration"]) / 2, 2),
                "system_delay": round((event_multipliers["base"]["system_delay"] + event_multipliers["v1"]["system_delay"]) / 2, 2),
                "queue": round((event_multipliers["base"]["queue"] + event_multipliers["v1"]["queue"]) / 2, 2),
                "emergency": round((event_multipliers["base"]["emergency"] + event_multipliers["v1"]["emergency"]) / 2, 2),
            },
            "bus_penalty_per_100pct": 0.08,
            "pedestrian_penalty_per_100pct": 0.12,
            "pulse_penalty_max": 0.25,
            "pulse_period_s": PEDESTRIAN_PULSE_PERIOD_S,
        },
    }


def main() -> None:
    print("=" * 60)
    print("PHASE 6: Exporting presentation data")
    print("=" * 60)

    manifest = build_manifest()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest -> {DATA_DIR / 'manifest.json'}")
    print(f"Networks -> {NETWORKS_DIR}")
    print(f"Playback -> {PLAYBACK_DIR}")


if __name__ == "__main__":
    main()
