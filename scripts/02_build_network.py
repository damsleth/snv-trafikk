#!/usr/bin/env python3
"""Build SUMO network from OSM data and create PGF lane configuration variants."""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NETWORK_DIR = PROJECT_ROOT / "network"
OSM_FILE = NETWORK_DIR / "osm" / "fornebu.osm.xml"
BASE_NET = NETWORK_DIR / "base" / "fornebu.net.xml"
BASE_EDG = NETWORK_DIR / "base" / "fornebu.edg.xml"
BASE_NOD = NETWORK_DIR / "base" / "fornebu.nod.xml"
BASE_CON = NETWORK_DIR / "base" / "fornebu.con.xml"
BASE_TLL = NETWORK_DIR / "base" / "fornebu.tll.xml"

CORRIDOR_X_MIN = 3200
CORRIDOR_X_MAX = 3900
SEGMENT_BOUNDS = {
    "C": (1700, 2315),
    "B": (2315, 2505),
    "A": (2505, 3050),
}
BUS_LANE_ALLOWED = "bus coach taxi emergency"
FUTURE_CONNECTOR_ID = "custom_5000"
FUTURE_CONNECTOR_NAME = "Fremtidig forbindelse"
FUTURE_CONNECTOR_SPEED = 11.11  # 40 km/h
FUTURE_CONNECTOR_LANES = 1
FUTURE_CONNECTOR_SHAPES = {
    FUTURE_CONNECTOR_ID: (
        "1304784222",
        "671838807",
        "3269.79,1691.76 3248.00,1720.00 3220.00,1756.00 3190.00,1797.00 3155.79,1845.39",
    ),
    f"-{FUTURE_CONNECTOR_ID}": (
        "671838807",
        "1304784222",
        "3155.79,1845.39 3190.00,1797.00 3220.00,1756.00 3248.00,1720.00 3269.79,1691.76",
    ),
}
FUTURE_CONNECTOR_CONNECTIONS = [
    {"from": "13798308#2", "to": FUTURE_CONNECTOR_ID, "fromLane": "0", "toLane": "0"},
    {"from": "13798308#2", "to": FUTURE_CONNECTOR_ID, "fromLane": "1", "toLane": "0"},
]

def find_tool(name: str) -> str:
    """Find a SUMO binary in venv or PATH."""
    venv = PROJECT_ROOT / ".venv" / "bin" / name
    if venv.exists():
        return str(venv)
    result = subprocess.run(["which", name], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    raise FileNotFoundError(f"SUMO tool '{name}' not found")


def create_typemap(output: Path):
    """Create a SUMO type mapping file for Norwegian roads."""
    root = ET.Element("types")
    types_data = [
        ("highway.motorway", 6, 33.33, 2, "true"),
        ("highway.motorway_link", 5, 22.22, 1, "true"),
        ("highway.trunk", 5, 22.22, 2, "false"),
        ("highway.trunk_link", 4, 16.67, 1, "false"),
        ("highway.primary", 4, 16.67, 2, "false"),
        ("highway.primary_link", 3, 13.89, 1, "false"),
        ("highway.secondary", 3, 13.89, 2, "false"),
        ("highway.secondary_link", 2, 13.89, 1, "false"),
        ("highway.tertiary", 2, 11.11, 1, "false"),
        ("highway.tertiary_link", 2, 11.11, 1, "false"),
        ("highway.residential", 1, 8.33, 1, "false"),
        ("highway.unclassified", 1, 8.33, 1, "false"),
        ("highway.living_street", 1, 5.56, 1, "false"),
    ]
    for type_id, priority, speed, num_lanes, oneway in types_data:
        t = ET.SubElement(root, "type")
        t.set("id", type_id)
        t.set("priority", str(priority))
        t.set("speed", f"{speed:.2f}")
        t.set("numLanes", str(num_lanes))
        t.set("oneway", oneway)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(output), xml_declaration=True, encoding="utf-8")


def step1_osm_to_base():
    """Convert OSM to base SUMO network."""
    if not OSM_FILE.exists():
        raise RuntimeError(f"OSM file not found at {OSM_FILE}. Run scripts/01_fetch_osm.py first.")

    netconvert = find_tool("netconvert")
    BASE_NET.parent.mkdir(parents=True, exist_ok=True)

    type_file = NETWORK_DIR / "osm" / "typemap.xml"
    create_typemap(type_file)

    cmd = [
        netconvert,
        "--osm-files", str(OSM_FILE),
        "--output-file", str(BASE_NET),
        "--type-files", str(type_file),
        "--geometry.remove", "true",
        "--ramps.guess", "true",
        "--junctions.join", "true",
        "--roundabouts.guess", "true",
        "--keep-edges.by-vclass", "passenger",
        "--remove-edges.by-type",
        "highway.footway,highway.cycleway,highway.path,highway.pedestrian,highway.steps,highway.service",
        "--proj.utm", "true",
        "--default.junctions.radius", "12",
        "--junctions.internal-link-detail", "5",
        "--output.street-names", "true",
        "--output.original-names", "true",
        # Also write plain XML for editing
        "--plain-output-prefix", str(NETWORK_DIR / "base" / "fornebu"),
    ]

    print("Running netconvert (OSM → base network)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"netconvert failed (code {result.returncode}):\n{result.stderr[:1000]}")
    if result.stderr.strip():
        print(f"netconvert warnings:\n{result.stderr[:1000]}")
    if not BASE_NET.exists():
        raise RuntimeError("netconvert failed to produce network")
    print(f"  Base network → {BASE_NET}")
    print(f"  Edge definitions → {BASE_EDG}")
    print(f"  Node definitions → {BASE_NOD}")


def step1b_add_future_connector() -> None:
    """Add the future 1+1 connector between søndre rundkjøring and Spydkasteren.

    OSM currently reflects the Fornebubanen worksite and does not show the
    near-term reopening of the direct link west of Rolfsbuktveien. We patch the
    plain edge definitions so the simulation network matches the intended future
    street layout instead of today's temporary closure.
    """
    tree = ET.parse(str(BASE_EDG))
    root = tree.getroot()
    existing_ids = {edge.get("id") for edge in root.findall("edge")}

    updated = False
    for edge_id, (from_node, to_node, shape) in FUTURE_CONNECTOR_SHAPES.items():
        if edge_id in existing_ids:
            continue
        edge = ET.SubElement(root, "edge")
        edge.set("id", edge_id)
        edge.set("from", from_node)
        edge.set("to", to_node)
        edge.set("name", FUTURE_CONNECTOR_NAME)
        edge.set("priority", "2")
        edge.set("type", "highway.tertiary")
        edge.set("numLanes", str(FUTURE_CONNECTOR_LANES))
        edge.set("speed", f"{FUTURE_CONNECTOR_SPEED:.2f}")
        edge.set("shape", shape)
        edge.set("spreadType", "center")
        updated = True

    if updated:
        ET.indent(tree, space="    ")
        tree.write(str(BASE_EDG), xml_declaration=True, encoding="utf-8")
        print(f"  Added future connector to plain edges → {BASE_EDG}")
    else:
        print("  Future connector already present in plain edges")

    con_tree = ET.parse(str(BASE_CON))
    con_root = con_tree.getroot()
    existing_connections = {
        (
            conn.get("from"),
            conn.get("to"),
            conn.get("fromLane"),
            conn.get("toLane"),
        )
        for conn in con_root.findall("connection")
    }
    added_connections = 0
    for attrs in FUTURE_CONNECTOR_CONNECTIONS:
        key = (attrs["from"], attrs["to"], attrs["fromLane"], attrs["toLane"])
        if key in existing_connections:
            continue
        connection = ET.SubElement(con_root, "connection")
        for attr_name, attr_value in attrs.items():
            connection.set(attr_name, attr_value)
        added_connections += 1

    if added_connections:
        ET.indent(con_tree, space="    ")
        con_tree.write(str(BASE_CON), xml_declaration=True, encoding="utf-8")
        print(f"  Added future connector routing to plain connections → {BASE_CON}")
    else:
        print("  Future connector routing already present in plain connections")


def step1c_rebuild_base_from_plain() -> None:
    """Rebuild the base network so custom future links become routable."""
    netconvert = find_tool("netconvert")
    cmd = [
        netconvert,
        "--node-files", str(BASE_NOD),
        "--edge-files", str(BASE_EDG),
        "--connection-files", str(BASE_CON),
        "--tllogic-files", str(BASE_TLL),
        "--output-file", str(BASE_NET),
        "--output.street-names", "true",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not BASE_NET.exists():
        raise RuntimeError(f"failed to rebuild base network with future connector:\n{result.stderr[:1000]}")

    print(f"  Rebuilt base network with future connector → {BASE_NET}")


def classify_segment(mid_y: float) -> str | None:
    """Map edge midpoint to corridor segment A/B/C."""
    for segment, (lower, upper) in SEGMENT_BOUNDS.items():
        if lower <= mid_y < upper:
            return segment
    return None


def step2_find_snaroyveien_edges() -> dict:
    """Identify Snarøyveien corridor edges by segment and direction."""
    import sumolib

    net = sumolib.net.readNet(str(BASE_NET))

    edges: dict[str, dict[str, list[str]] | list[str]] = {
        "northbound": {"A": [], "B": [], "C": []},
        "southbound": {"A": [], "B": [], "C": []},
        "all_names": [],
    }
    all_names = set()

    for edge in net.getEdges():
        eid = edge.getID()
        if eid.startswith(":"):
            continue
        name = (edge.getName() or "").lower()
        if "snarøyveien" not in name and "snaroyveien" not in name:
            continue

        from_y = edge.getFromNode().getCoord()[1]
        to_y = edge.getToNode().getCoord()[1]
        from_x = edge.getFromNode().getCoord()[0]
        to_x = edge.getToNode().getCoord()[0]
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        segment = classify_segment(mid_y)
        if segment is None or not (CORRIDOR_X_MIN <= mid_x <= CORRIDOR_X_MAX):
            continue

        all_names.add(edge.getName() or eid)
        if to_y > from_y:
            edges["northbound"][segment].append(eid)
        else:
            edges["southbound"][segment].append(eid)

    edges["all_names"] = sorted(all_names)
    return edges


def build_variant_layout(
    snv_edges: dict,
    northbound_by_segment: dict[str, tuple[int, bool]],
    southbound_by_segment: dict[str, tuple[int, bool]],
    speed_kmh: float = 40.0,
) -> dict[str, dict[str, str | bool]]:
    """Construct per-edge lane count and bus-lane configuration."""
    config: dict[str, dict[str, str | bool]] = {}
    speed_ms = speed_kmh / 3.6

    for direction_key, segment_map, spec_map in [
        ("northbound", snv_edges["northbound"], northbound_by_segment),
        ("southbound", snv_edges["southbound"], southbound_by_segment),
    ]:
        _ = direction_key
        for segment, edge_ids in segment_map.items():
            target_lanes, has_bus_lane = spec_map[segment]
            for edge_id in edge_ids:
                config[edge_id] = {
                    "numLanes": str(target_lanes),
                    "speed": f"{speed_ms:.2f}",
                    "bus_lane": has_bus_lane,
                }
    return config


def apply_lane_permissions(net_file: Path, lane_config: dict[str, dict[str, str | bool]]) -> None:
    """Set lane-level permissions after netconvert has rebuilt connections."""
    tree = ET.parse(str(net_file))
    root = tree.getroot()

    for edge_elem in root.iter("edge"):
        edge_id = edge_elem.get("id", "")
        if edge_id not in lane_config:
            continue

        bus_lane = bool(lane_config[edge_id]["bus_lane"])
        lanes = edge_elem.findall("lane")
        bus_lane_index = str(len(lanes) - 1) if lanes else None
        for lane in lanes:
            lane.attrib.pop("allow", None)
            if bus_lane and lane.get("index") == bus_lane_index:
                lane.attrib.pop("disallow", None)
                lane.set("allow", BUS_LANE_ALLOWED)

    ET.indent(tree, space="  ")
    tree.write(str(net_file), xml_declaration=True, encoding="utf-8")


def step4_create_variant(variant_name: str, lane_config: dict[str, dict[str, str | bool]]):
    """Create a network variant by patching edge lane counts and permissions."""
    netconvert = find_tool("netconvert")
    proposed_dir = NETWORK_DIR / "proposed"
    proposed_dir.mkdir(parents=True, exist_ok=True)

    # Create a minimal edge-patch file with just the modified edges
    patch_root = ET.Element("edges")
    for edge_id, edge_config in sorted(lane_config.items()):
        patch_edge = ET.SubElement(patch_root, "edge")
        patch_edge.set("id", edge_id)
        patch_edge.set("numLanes", str(edge_config["numLanes"]))
        patch_edge.set("speed", str(edge_config["speed"]))

    variant_patch = proposed_dir / f"{variant_name}.patch.edg.xml"
    patch_tree = ET.ElementTree(patch_root)
    ET.indent(patch_tree, space="  ")
    patch_tree.write(str(variant_patch), xml_declaration=True, encoding="utf-8")

    # Use netconvert to apply the patch to the base network
    output_net = proposed_dir / f"{variant_name}.net.xml"
    cmd = [
        netconvert,
        "--sumo-net-file", str(BASE_NET),
        "--edge-files", str(variant_patch),
        "--output-file", str(output_net),
        "--output.street-names", "true",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not output_net.exists():
        raise RuntimeError(
            f"netconvert failed for {variant_name} (code {result.returncode}):\n{result.stderr[:500]}"
        )

    apply_lane_permissions(output_net, lane_config)

    print(f"  {variant_name} ({len(lane_config)} edges patched) -> {output_net}")
    return output_net


def step5_roundabout_params():
    """Calibrate roundabout gap acceptance for any untyped vehicle.

    The primary calibration is set on the "car" vType in
    scripts/03_generate_demand.py, which is what generated traffic references.
    This additional only redefines SUMO's built-in DEFAULT_VEHTYPE so that any
    vehicle inserted without an explicit type (e.g. ad-hoc TraCI vehicles)
    inherits the same gap-acceptance behaviour. The previous id="default" was a
    plain unused type that no vehicle referenced, so it never took effect.
    """
    add_file = NETWORK_DIR / "signals" / "roundabout_params.add.xml"
    add_file.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("additional")
    vtype = ET.SubElement(root, "vType")
    vtype.set("id", "DEFAULT_VEHTYPE")
    vtype.set("jmTimegapMinor", "1.5")
    vtype.set("jmDriveAfterYellowTime", "1.0")
    vtype.set("lcStrategic", "1.0")
    vtype.set("lcCooperative", "1.0")
    vtype.set("speedFactor", "normc(1.0,0.1,0.8,1.2)")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(add_file), xml_declaration=True, encoding="utf-8")
    print(f"  Roundabout params → {add_file}")


def step6_rolfsbukt_miljogaterestriction():
    """Generate an additional file that slows Rolfsbuktveien to model a miljøgate.

    The kommunestyre voted to convert Rolfsbuktveien to a "miljøgate" with
    traffic calming (fartsdumper, chicanes). This reduces effective capacity
    and speed to ~15 km/h, discouraging through-traffic.
    """
    import sumolib

    net = sumolib.net.readNet(str(BASE_NET))
    add_file = NETWORK_DIR / "signals" / "rolfsbukt_miljogate.add.xml"
    add_file.parent.mkdir(parents=True, exist_ok=True)

    # Collect all Rolfsbuktveien edges (not Rolfsbuktalléen)
    rolfsbukt_edges = []
    for edge in net.getEdges():
        name = (edge.getName() or "").lower()
        if "rolfsbuktveien" in name:
            rolfsbukt_edges.append(edge.getID())

    root = ET.Element("additional")
    # Use variableSpeedSign to enforce 15 km/h on all Rolfsbuktveien lanes.
    MILJOGATE_SPEED = 15.0 / 3.6  # 15 km/h → m/s
    for i, eid in enumerate(sorted(rolfsbukt_edges)):
        edge = net.getEdge(eid)
        for lane in edge.getLanes():
            vss = ET.SubElement(root, "variableSpeedSign")
            vss.set("id", f"miljogate_vss_{i}_{lane.getIndex()}")
            vss.set("lanes", lane.getID())
            step = ET.SubElement(vss, "step")
            step.set("time", "0")
            step.set("speed", f"{MILJOGATE_SPEED:.2f}")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(add_file), xml_declaration=True, encoding="utf-8")
    print(f"  Rolfsbukt miljøgate restriction → {add_file} ({len(rolfsbukt_edges)} edges)")
    return add_file


def build_all():
    """Build base network and all variants."""
    print("=" * 60)
    print("PHASE 1: Building SUMO network from OSM data")
    print("=" * 60)

    # Step 1: OSM → base network + plain XML
    step1_osm_to_base()
    step1b_add_future_connector()
    step1c_rebuild_base_from_plain()

    # Step 2: Identify Snarøyveien edges
    print("\nIdentifying Snarøyveien corridor edges...")
    snv_edges = step2_find_snaroyveien_edges()
    nb_total = sum(len(edges) for edges in snv_edges["northbound"].values())
    sb_total = sum(len(edges) for edges in snv_edges["southbound"].values())
    print(f"  Found {nb_total} NB + {sb_total} SB corridor edges")
    print(f"  Names: {snv_edges['all_names']}")

    # Step 4: Roundabout calibration
    print("\nCalibrating roundabout parameters...")
    step5_roundabout_params()

    # Step 5: Create variant networks
    print("\nCreating network variants...")

    v1_layout = build_variant_layout(
        snv_edges,
        northbound_by_segment={"A": (3, True), "B": (2, True), "C": (2, True)},
        southbound_by_segment={"A": (2, False), "B": (2, False), "C": (2, False)},
    )
    v2_layout = build_variant_layout(
        snv_edges,
        northbound_by_segment={"A": (3, True), "B": (2, True), "C": (2, True)},
        southbound_by_segment={"A": (2, True), "B": (2, True), "C": (2, True)},
    )
    v3_layout = build_variant_layout(
        snv_edges,
        northbound_by_segment={"A": (3, True), "B": (2, True), "C": (3, True)},
        southbound_by_segment={"A": (2, False), "B": (2, False), "C": (2, False)},
    )

    step4_create_variant("fornebu_v1", v1_layout)
    step4_create_variant("fornebu_v2", v2_layout)
    step4_create_variant("fornebu_v3", v3_layout)

    # Step 6: Rolfsbuktveien miljøgate restriction
    print("\nGenerating Rolfsbuktveien miljøgate restriction...")
    step6_rolfsbukt_miljogaterestriction()

    print("\n" + "=" * 60)
    print("All networks built!")
    print(f"  Base:  {BASE_NET}")
    print(f"  V1:    {NETWORK_DIR / 'proposed' / 'fornebu_v1.net.xml'}")
    print(f"  V2:    {NETWORK_DIR / 'proposed' / 'fornebu_v2.net.xml'}")
    print(f"  V3:    {NETWORK_DIR / 'proposed' / 'fornebu_v3.net.xml'}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        build_all()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
