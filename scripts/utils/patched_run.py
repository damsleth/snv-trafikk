"""Build and run patched SUMO scenarios from advanced workbench exports."""

from __future__ import annotations

import json
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.config import PROJECT_ROOT, SIMULATION_BEGIN_S, SIMULATION_END_S, queue_length_km
from scripts.utils.patch_generator import build_metadata, write_patch_bundle
from scripts.utils.presentation_playback import build_kpis_from_stats, export_playback_from_files
from scripts.utils.scenario_catalog import SCENARIOS


PATCH_RUNS_DIR = PROJECT_ROOT / "tmp" / "patched_runs"


def find_tool(name: str) -> str:
    for candidate in (PROJECT_ROOT / ".venv" / "lib").glob("python*/site-packages/sumo/bin/*"):
        if candidate.name == name and candidate.exists():
            return str(candidate)

    venv = PROJECT_ROOT / ".venv" / "bin" / name
    if venv.exists():
        return str(venv)

    result = subprocess.run(["which", name], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    raise FileNotFoundError(f"SUMO tool '{name}' not found")


def resolve_target_scenario(family: str, period: str, concert: bool = False) -> str:
    if period not in {"morning", "afternoon"}:
        raise ValueError("Patched reruns are only supported for morning and afternoon scenarios")
    event_name = f"{family}_event_{period}"
    scenario_name = event_name if concert and event_name in SCENARIOS else f"{family}_{period}"
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario selection: {scenario_name}")
    return scenario_name


def create_run_workspace(scenario_name: str) -> Path:
    run_id = f"{scenario_name}_{time.strftime('%Y%m%d_%H%M%S')}"
    workspace = PATCH_RUNS_DIR / run_id
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def build_patched_network(base_network: Path, patch_dir: Path, output_net: Path) -> None:
    netconvert = find_tool("netconvert")
    command = [
        netconvert,
        "--sumo-net-file",
        str(base_network),
        "--output-file",
        str(output_net),
        "--output.street-names",
        "true",
    ]

    edge_patch = patch_dir / "advanced_patch.edg.xml"
    connection_patch = patch_dir / "advanced_patch.con.xml"
    if edge_patch.exists():
        command.extend(["--edge-files", str(edge_patch)])
    if connection_patch.exists():
        command.extend(["--connection-files", str(connection_patch)])

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not output_net.exists():
        raise RuntimeError(f"netconvert failed to build patched network:\n{result.stderr[:1000]}")


def apply_artifact_lane_permissions(net_file: Path, package: dict) -> None:
    artifacts_by_edge: dict[str, list[dict]] = {}
    for artifact in package.get("artifacts", []):
        if artifact.get("type") not in {"sidewalk", "cycleway"}:
            continue
        artifacts_by_edge.setdefault(artifact["edge_id"], []).append(artifact)

    if not artifacts_by_edge:
        return

    edge_edits = {patch["edge_id"]: patch for patch in package.get("edge_edits", [])}
    tree = ET.parse(str(net_file))
    root = tree.getroot()

    for edge_elem in root.iter("edge"):
        edge_id = edge_elem.get("id", "")
        artifacts = artifacts_by_edge.get(edge_id)
        if not artifacts:
            continue

        patch = edge_edits.get(edge_id, {})
        base = patch.get("base", {})
        base_lane_count = int(patch.get("lanes") or base.get("lanes") or len(edge_elem.findall("lane")) or 1)
        lanes = edge_elem.findall("lane")
        lane_index = min(base_lane_count, len(lanes))
        for artifact in artifacts:
            if lane_index >= len(lanes):
                break
            lane = lanes[lane_index]
            lane.attrib.pop("disallow", None)
            lane.attrib.pop("allow", None)
            lane.set("allow", "pedestrian" if artifact.get("type") == "sidewalk" else "bicycle")
            if artifact.get("width_m"):
                lane.set("width", f"{float(artifact['width_m']):.1f}")
            lane_index += 1

    ET.indent(tree, space="  ")
    tree.write(str(net_file), xml_declaration=True, encoding="utf-8")


def create_sumo_config(
    config_path: Path,
    network_path: Path,
    route_files: str,
    additional_files: list[str],
    output_dir: Path,
    seed: int,
) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<configuration>",
        "  <input>",
        f'    <net-file value="{network_path}"/>',
        f'    <route-files value="{route_files}"/>',
    ]
    if additional_files:
        lines.append(f'    <additional-files value="{",".join(additional_files)}"/>')
    lines += [
        "  </input>",
        "  <time>",
        f'    <begin value="{SIMULATION_BEGIN_S}"/>',
        f'    <end value="{SIMULATION_END_S}"/>',
        '    <step-length value="1.0"/>',
        "  </time>",
        "  <processing>",
        '    <lateral-resolution value="0.8"/>',
        '    <collision.action value="warn"/>',
        '    <time-to-teleport value="300"/>',
        "  </processing>",
        "  <random_number>",
        f'    <seed value="{seed}"/>',
        "  </random_number>",
        "  <output>",
        f'    <tripinfo-output value="{output_dir / "tripinfo.xml"}"/>',
        f'    <summary-output value="{output_dir / "summary.xml"}"/>',
        f'    <fcd-output value="{output_dir / "fcd.xml"}"/>',
        f'    <statistic-output value="{output_dir / "stats.xml"}"/>',
        "  </output>",
        "  <fcd_device>",
        '    <device.fcd.period value="5"/>',
        "  </fcd_device>",
        "</configuration>",
    ]
    config_path.write_text("\n".join(lines), encoding="utf-8")


def parse_stats(output_dir: Path) -> dict:
    stats: dict[str, float | int | str | bool] = {}

    tripinfo_file = output_dir / "tripinfo.xml"
    if tripinfo_file.exists():
        tree = ET.parse(str(tripinfo_file))
        trips = tree.getroot().findall("tripinfo")
        regular = [trip for trip in trips if not trip.get("id", "").startswith("emer_")]
        emergency = [trip for trip in trips if trip.get("id", "").startswith("emer_")]

        durations = [float(trip.get("duration", 0)) for trip in regular]
        waiting_times = [float(trip.get("waitingTime", 0)) for trip in regular]
        time_losses = [float(trip.get("timeLoss", 0)) for trip in regular]
        if durations:
            stats["completed_vehicles"] = len(durations)
            stats["avg_duration_s"] = sum(durations) / len(durations)
            stats["max_duration_s"] = max(durations)
            stats["avg_waiting_time_s"] = sum(waiting_times) / len(waiting_times)
            stats["max_waiting_time_s"] = max(waiting_times)
            stats["avg_time_loss_s"] = sum(time_losses) / len(time_losses)
            stats["completed_time_loss_h"] = sum(time_losses) / 3600.0

        if emergency:
            emergency_durations = [float(trip.get("duration", 0)) for trip in emergency]
            emergency_losses = [float(trip.get("timeLoss", 0)) for trip in emergency]
            stats["emergency_count"] = len(emergency_durations)
            stats["emergency_avg_duration_s"] = sum(emergency_durations) / len(emergency_durations)
            stats["emergency_max_duration_s"] = max(emergency_durations)
            stats["emergency_avg_time_loss_s"] = sum(emergency_losses) / len(emergency_losses)

    summary_file = output_dir / "summary.xml"
    if summary_file.exists():
        tree = ET.parse(str(summary_file))
        steps = tree.getroot().findall("step")
        if steps:
            waiting_series = [int(step.get("waiting", 0)) for step in steps]
            halting_series = [int(step.get("halting", 0)) for step in steps]
            blocked_vehicle_seconds = sum(waiting_series)
            queued_vehicle_seconds = sum(waiting + halting for waiting, halting in zip(waiting_series, halting_series))
            stats["blocked_vehicle_h"] = blocked_vehicle_seconds / 3600.0
            stats["queued_vehicle_h"] = queued_vehicle_seconds / 3600.0
            stats["peak_waiting"] = max(waiting_series)
            stats["peak_queue_proxy"] = max(waiting + halting for waiting, halting in zip(waiting_series, halting_series))

    stats_file = output_dir / "stats.xml"
    if stats_file.exists():
        tree = ET.parse(str(stats_file))
        root = tree.getroot()
        vehicles = root.find(".//vehicles")
        if vehicles is not None:
            loaded = int(vehicles.get("loaded", 0))
            inserted = int(vehicles.get("inserted", 0))
            stats["loaded"] = loaded
            stats["inserted"] = inserted
            stats["waiting"] = int(vehicles.get("waiting", 0))
            stats["teleports"] = int(vehicles.get("teleports", 0))
            stats["not_inserted"] = loaded - inserted

    stats["system_delay_h"] = float(stats.get("completed_time_loss_h", 0)) + float(stats.get("blocked_vehicle_h", 0))
    stats["queue_length_km"] = queue_length_km(int(stats.get("not_inserted", 0)) + int(stats.get("peak_waiting", 0)))
    return stats


def run_sumo(config_path: Path) -> tuple[int, str]:
    sumo_binary = find_tool("sumo")
    result = subprocess.run(
        [
            sumo_binary,
            "-c",
            str(config_path),
            "--no-warnings",
            "true",
            "--verbose",
            "false",
            "--no-step-log",
            "true",
            "--ignore-route-errors",
            "false",
            "--routing-algorithm",
            "astar",
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    return result.returncode, result.stderr[:2000].strip()


def run_patched_scenario(package: dict, family: str, period: str, concert: bool = False, seed: int = 1) -> dict:
    scenario_name = resolve_target_scenario(family, period, concert)
    scenario = SCENARIOS[scenario_name]
    workspace = create_run_workspace(scenario_name)
    patch_dir = workspace / "patch_bundle"
    output_dir = workspace / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    write_patch_bundle(package, patch_dir)

    patched_net = workspace / "patched.net.xml"
    build_patched_network(Path(str(scenario["network"])), patch_dir, patched_net)
    apply_artifact_lane_permissions(patched_net, package)

    config_path = workspace / f"{scenario_name}_seed{seed}.cfg"
    additional = [path for path in scenario.get("additional", []) if Path(path).exists()]
    create_sumo_config(
        config_path=config_path,
        network_path=patched_net,
        route_files=str(scenario["routes"]),
        additional_files=additional,
        output_dir=output_dir,
        seed=seed,
    )

    returncode, error_text = run_sumo(config_path)
    if returncode != 0:
        raise RuntimeError(error_text or "SUMO failed for the patched scenario")

    stats = parse_stats(output_dir)
    playback = export_playback_from_files(
        network_path=patched_net,
        fcd_path=output_dir / "fcd.xml",
        tripinfo_path=output_dir / "tripinfo.xml",
        summary_path=output_dir / "summary.xml",
    )

    metadata = build_metadata(package)
    response = {
        "run_id": workspace.name,
        "scenario": scenario_name,
        "family": family,
        "period": period,
        "concert": concert,
        "seed": seed,
        "playback": playback,
        "stats": stats,
        "kpis": build_kpis_from_stats(stats),
        "warnings": [],
        "unsupported_artifacts": metadata["unsupported_artifacts"],
        "patch_bundle_dir": str(patch_dir.relative_to(PROJECT_ROOT)),
        "patched_network": str(patched_net.relative_to(PROJECT_ROOT)),
    }
    if metadata["unsupported_artifacts"]:
        response["warnings"].append("Noen artefakter er bare dokumentert i metadata og er ikke anvendt i SUMO-nettet.")

    (workspace / "response.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
    return response
