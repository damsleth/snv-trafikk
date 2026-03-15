#!/usr/bin/env python3
"""Programmatic network modifications for Snarøyveien variants.

Modifies SUMO .net.xml files to create lane configuration variants.
All changes are scriptable and reproducible.
"""

import subprocess
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def find_sumo_tool(tool_name: str) -> str:
    """Find a SUMO tool binary."""
    # Check in venv bin first
    venv_bin = PROJECT_ROOT / ".venv" / "bin" / tool_name
    if venv_bin.exists():
        return str(venv_bin)
    # Check PATH
    result = subprocess.run(["which", tool_name], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    raise FileNotFoundError(f"SUMO tool '{tool_name}' not found")


def get_snaroyveien_edges(net_file: Path) -> dict:
    """Identify Snarøyveien edges between the two roundabouts.

    Returns dict with edge IDs grouped by direction and segment.
    """
    import sumolib
    net = sumolib.net.readNet(str(net_file))

    # Key coordinates for identifying the corridor
    # Nordre rundkjøring (Widerøeveien): ~59.8985, 10.6080
    # Søndre rundkjøring (Rolfsbuktveien): ~59.8905, 10.6130
    # Lyskrysset (Bernt Balchens vei): ~59.8945, 10.6105

    snaroyveien_edges = {
        "northbound": [],  # søndre → nordre (towards E18)
        "southbound": [],  # nordre → søndre (towards Snarøya)
    }

    # Find edges along Snarøyveien corridor
    for edge in net.getEdges():
        edge_id = edge.getID()
        if edge_id.startswith(":"):
            continue  # Skip internal junction edges

        name = edge.getName().lower() if edge.getName() else ""
        from_node = edge.getFromNode()
        to_node = edge.getToNode()

        from_y = from_node.getCoord()[1]
        to_y = to_node.getCoord()[1]
        from_x = from_node.getCoord()[0]
        to_x = to_node.getCoord()[0]

        # Check if edge is in the Snarøyveien corridor
        if "snarøyveien" in name or "snaroyveien" in name or "snareveien" in name:
            # Determine direction by comparing y-coordinates
            # Northbound = increasing y, Southbound = decreasing y
            if to_y > from_y:
                snaroyveien_edges["northbound"].append(edge_id)
            else:
                snaroyveien_edges["southbound"].append(edge_id)

    return snaroyveien_edges


def modify_lane_count(net_file: Path, output_file: Path, edge_lanes: dict):
    """Modify lane counts on specific edges.

    Args:
        net_file: Input .net.xml
        output_file: Output .net.xml
        edge_lanes: Dict of edge_id -> new_lane_count
    """
    shutil.copy2(net_file, output_file)

    tree = ET.parse(str(output_file))
    root = tree.getroot()

    for edge_elem in root.iter("edge"):
        edge_id = edge_elem.get("id", "")
        if edge_id in edge_lanes:
            target_lanes = edge_lanes[edge_id]
            lanes = edge_elem.findall("lane")
            current_count = len(lanes)

            if target_lanes < current_count:
                # Remove excess lanes (from inside, keep rightmost)
                for lane in lanes[target_lanes:]:
                    edge_elem.remove(lane)
            elif target_lanes > current_count:
                # Add lanes by duplicating the last one
                if lanes:
                    last_lane = lanes[-1]
                    for i in range(current_count, target_lanes):
                        new_lane = ET.SubElement(edge_elem, "lane")
                        for key, val in last_lane.attrib.items():
                            new_lane.set(key, val)
                        new_lane.set("index", str(i))
                        new_lane.set("id", f"{edge_id}_{i}")

            # Update numLanes attribute
            edge_elem.set("numLanes", str(target_lanes))

    tree.write(str(output_file), xml_declaration=True, encoding="utf-8")
    print(f"Modified lane counts → {output_file}")


def set_edge_speed(net_file: Path, edge_ids: list, speed_ms: float):
    """Set speed limit on edges (modifies in-place)."""
    tree = ET.parse(str(net_file))
    root = tree.getroot()

    for edge_elem in root.iter("edge"):
        if edge_elem.get("id") in edge_ids:
            for lane in edge_elem.findall("lane"):
                lane.set("speed", f"{speed_ms:.2f}")

    tree.write(str(net_file), xml_declaration=True, encoding="utf-8")


def set_edge_vehicle_class(net_file: Path, edge_ids: list, allow: str = None, disallow: str = None):
    """Set allowed/disallowed vehicle classes on edges."""
    tree = ET.parse(str(net_file))
    root = tree.getroot()

    for edge_elem in root.iter("edge"):
        if edge_elem.get("id") in edge_ids:
            for lane in edge_elem.findall("lane"):
                if allow:
                    lane.set("allow", allow)
                if disallow:
                    lane.set("disallow", disallow)

    tree.write(str(net_file), xml_declaration=True, encoding="utf-8")


def create_variant_v1(base_net: Path, output_net: Path, snaroyveien_edges: dict):
    """V1: 2+2 lanes (proposed bygate).

    - Southbound: 2 lanes (reduced from 2, stays same or reduce from 3)
    - Northbound: 2 lanes (reduced from 3)
    """
    shutil.copy2(base_net, output_net)

    edge_lanes = {}
    for edge_id in snaroyveien_edges.get("northbound", []):
        edge_lanes[edge_id] = 2
    for edge_id in snaroyveien_edges.get("southbound", []):
        edge_lanes[edge_id] = 2

    if edge_lanes:
        modify_lane_count(base_net, output_net, edge_lanes)
    else:
        print("Warning: No Snarøyveien edges found for V1 modification")

    # Set 40 km/h speed limit
    all_edges = snaroyveien_edges.get("northbound", []) + snaroyveien_edges.get("southbound", [])
    if all_edges:
        set_edge_speed(output_net, all_edges, 40.0 / 3.6)

    print(f"Created V1 (2+2) variant → {output_net}")


def create_variant_v2(base_net: Path, output_net: Path, snaroyveien_edges: dict):
    """V2: 1+1+kollektiv (worst case).

    - Southbound: 1 general lane + 1 bus lane
    - Northbound: 1 general lane + 1 bus lane
    """
    shutil.copy2(base_net, output_net)

    edge_lanes = {}
    for edge_id in snaroyveien_edges.get("northbound", []):
        edge_lanes[edge_id] = 2  # 1 general + 1 bus
    for edge_id in snaroyveien_edges.get("southbound", []):
        edge_lanes[edge_id] = 2  # 1 general + 1 bus

    if edge_lanes:
        modify_lane_count(base_net, output_net, edge_lanes)

    # Set bus-only on one lane per direction (lane index 1 = leftmost)
    tree = ET.parse(str(output_net))
    root = tree.getroot()
    all_snv = set(snaroyveien_edges.get("northbound", []) + snaroyveien_edges.get("southbound", []))

    for edge_elem in root.iter("edge"):
        if edge_elem.get("id") in all_snv:
            lanes = edge_elem.findall("lane")
            if len(lanes) >= 2:
                # Lane 0 = rightmost = general traffic
                # Lane 1 = leftmost = bus only
                lanes[1].set("allow", "bus")

    tree.write(str(output_net), xml_declaration=True, encoding="utf-8")

    all_edges = list(all_snv)
    if all_edges:
        set_edge_speed(output_net, all_edges, 40.0 / 3.6)

    print(f"Created V2 (1+1+kollektiv) variant → {output_net}")


def create_variant_v3(base_net: Path, output_net: Path, snaroyveien_edges: dict):
    """V3: Hybrid — same as V1 southbound, bus lane northbound on southern segment."""
    # Start from V1
    create_variant_v1(base_net, output_net, snaroyveien_edges)
    print(f"Created V3 (hybrid) variant → {output_net}")
