"""Helpers for exporting playback bundles from SUMO output files."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import sumolib

from scripts.config import (
    SIMULATION_END_S,
    SNAROYA_DESTINATION_EDGE_IDS,
    SNAROYA_ORIGIN_EDGE_IDS,
    lane_edge_id,
    queue_length_km,
)


PLAYBACK_INTERVAL_S = 5


def export_rolling_kpis_from_files(
    tripinfo_path: Path,
    summary_path: Path,
    interval_s: int = PLAYBACK_INTERVAL_S,
) -> list[dict]:
    if not tripinfo_path.exists():
        return []

    trips_snaroya_from = []
    trips_snaroya_to = []
    trips_emergency = []

    tree = ET.parse(str(tripinfo_path))
    for trip in tree.getroot().findall("tripinfo"):
        depart = float(trip.get("depart", "0"))
        arrival = float(trip.get("arrival", "-1"))
        duration = float(trip.get("duration", "0"))
        if arrival < 0:
            continue

        vehicle_id = trip.get("id", "")
        depart_edge = lane_edge_id(trip.get("departLane", ""))
        arrival_edge = lane_edge_id(trip.get("arrivalLane", ""))

        if vehicle_id.startswith("emer_"):
            trips_emergency.append((depart, arrival, duration))

        if depart_edge in SNAROYA_ORIGIN_EDGE_IDS:
            trips_snaroya_from.append((depart, arrival, duration))
        if arrival_edge in SNAROYA_DESTINATION_EDGE_IDS:
            trips_snaroya_to.append((depart, arrival, duration))

    queue_by_time: dict[int, int] = {}
    if summary_path.exists():
        context = ET.iterparse(str(summary_path), events=("end",))
        for _, elem in context:
            if elem.tag != "step":
                continue
            ts = int(round(float(elem.get("time", "0"))))
            queue_by_time[ts] = int(elem.get("waiting", "0")) + int(elem.get("halting", "0"))
            elem.clear()

    window_s = 300
    max_time = max(
        max((arrival for _, arrival, _ in trips_snaroya_from), default=0),
        max((arrival for _, arrival, _ in trips_snaroya_to), default=0),
        SIMULATION_END_S,
    )

    def avg_duration_in_window(trips: list[tuple[float, float, float]], center_s: int) -> float | None:
        durations = [duration for _, arrival, duration in trips if abs(arrival - center_s) <= window_s]
        if not durations:
            return None
        return round(sum(durations) / len(durations) / 60.0, 1)

    rolling = []
    for ts in range(0, int(max_time) + 1, interval_s):
        combined = [
            duration
            for _, arrival, duration in trips_snaroya_from + trips_snaroya_to
            if abs(arrival - ts) <= window_s
        ]
        rolling.append(
            {
                "t": ts,
                "snaroya_dur": round(sum(combined) / len(combined) / 60.0, 1) if combined else None,
                "snaroya_from": avg_duration_in_window(trips_snaroya_from, ts),
                "snaroya_to": avg_duration_in_window(trips_snaroya_to, ts),
                "emergency": avg_duration_in_window(trips_emergency, ts),
                "queue_km": queue_length_km(queue_by_time.get(ts, 0)),
            }
        )
    return rolling


def export_summary_series_from_file(summary_path: Path, interval_s: int = PLAYBACK_INTERVAL_S) -> list[list[int]]:
    if not summary_path.exists():
        return []

    queue_series = []
    previous_queue = None
    context = ET.iterparse(str(summary_path), events=("end",))
    for _, elem in context:
        if elem.tag != "step":
            continue
        time_s = int(round(float(elem.get("time", "0"))))
        if time_s % interval_s != 0:
            elem.clear()
            continue

        waiting = int(elem.get("waiting", "0"))
        halting = int(elem.get("halting", "0"))
        queue = waiting + halting
        growth = 0 if previous_queue is None else queue - previous_queue
        queue_series.append([time_s, waiting, halting, queue, growth])
        previous_queue = queue
        elem.clear()

    return queue_series


def export_playback_from_files(
    network_path: Path,
    fcd_path: Path,
    tripinfo_path: Path,
    summary_path: Path,
    interval_s: int = PLAYBACK_INTERVAL_S,
) -> dict:
    if not fcd_path.exists():
        return {
            "interval_s": interval_s,
            "frames": [],
            "summary": {"queue": []},
            "rolling_kpis": [],
            "max_edge_count": 0,
            "max_event_count": 0,
        }

    net = sumolib.net.readNet(str(network_path))
    frames = []
    max_edge_count = 0
    max_event_count = 0

    context = ET.iterparse(str(fcd_path), events=("end",))
    for _, elem in context:
        if elem.tag != "timestep":
            continue

        time_s = int(round(float(elem.get("time", "0"))))
        if time_s % interval_s != 0:
            elem.clear()
            continue

        edge_stats: dict[str, list[float]] = defaultdict(lambda: [0, 0.0, 0, 0])
        emergency_positions = []
        vehicle_positions = []

        for vehicle in elem.findall("vehicle"):
            lane_id = vehicle.get("lane", "")
            edge_id = lane_id.rsplit("_", 1)[0] if "_" in lane_id else lane_id
            speed = float(vehicle.get("speed", "0"))
            angle = float(vehicle.get("angle", "0"))
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

            lon, lat = net.convertXY2LonLat(float(vehicle.get("x", "0")), float(vehicle.get("y", "0")))
            kind = 0
            if vehicle_type == "emergency" or vehicle_id.startswith("emer_"):
                kind = 1
            elif vehicle_type == "event_car" or vehicle_id.startswith("event_"):
                kind = 2
            vehicle_positions.append(
                [
                    vehicle_id,
                    round(lat, 6),
                    round(lon, 6),
                    round(speed * 3.6, 1),
                    kind,
                    round(angle, 1),
                ]
            )

        edge_payload = {}
        for edge_id, values in edge_stats.items():
            count, speed_sum, emergency_count, event_count = values
            avg_speed_kmh = round((speed_sum / count) * 3.6, 1) if count else 0.0
            edge_payload[edge_id] = [int(count), avg_speed_kmh, int(emergency_count), int(event_count)]
            max_edge_count = max(max_edge_count, int(count))
            max_event_count = max(max_event_count, int(event_count))

        frames.append(
            {
                "t": time_s,
                "edges": edge_payload,
                "emergency": emergency_positions,
                "vehicles": vehicle_positions,
            }
        )
        elem.clear()

    return {
        "interval_s": interval_s,
        "frames": frames,
        "summary": {
            "queue": export_summary_series_from_file(summary_path, interval_s=interval_s),
        },
        "rolling_kpis": export_rolling_kpis_from_files(tripinfo_path, summary_path, interval_s=interval_s),
        "max_edge_count": max_edge_count,
        "max_event_count": max_event_count,
    }


def build_kpis_from_stats(stats: dict) -> dict:
    return {
        "avg_duration_min": round(float(stats.get("avg_duration_s", 0)) / 60.0, 1),
        "system_delay_h": round(float(stats.get("system_delay_h", 0)), 1),
        "queue_km": round(float(stats.get("queue_length_km", 0)), 1),
        "blocked_vehicles": round(float(stats.get("not_inserted", 0))),
        "peak_waiting": round(float(stats.get("peak_waiting", 0))),
        "emergency_avg_min": round(float(stats.get("emergency_avg_duration_s", 0)) / 60.0, 1),
        "snaroya_avg_min": round(float(stats.get("snaroya_avg_duration_s", 0)) / 60.0, 1),
    }
