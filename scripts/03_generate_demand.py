#!/usr/bin/env python3
"""Generate SUMO demand from the OD matrices in PGF appendix 1.

The official traffic analysis provides full OD matrices for scenario 1A/4A and
both peak hours. This script encodes those matrices directly instead of
flattening intersection turning counts into unrelated trips.
"""

import random
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMAND_DIR = PROJECT_ROOT / "demand"

ZONE_ORDER = [
    "snv_syd",
    "bbv_west",
    "e18_vest",
    "e18_ost",
    "ring3_nord",
    "snv_nordost",
    "wideroe_nordvest",
    "odd_nansens_vest",
    "snv_east",
    "martin_linges_sydost",
    "rolfsbukt_syd",
]

ZONE_LABELS = {
    "snv_syd": "Snarøyveien syd",
    "bbv_west": "Bernt Balchens vest",
    "e18_vest": "E18 vest (Sandvika-retning)",
    "e18_ost": "E18 øst (Oslo-retning)",
    "ring3_nord": "Ring 3 nord (Granfosstunnelen)",
    "snv_nordost": "Snarøyveien nordøst (lokal)",
    "wideroe_nordvest": "Widerøeveien nordvest",
    "odd_nansens_vest": "Odd Nansens vei vest",
    "snv_east": "Snarøyveien øst",
    "martin_linges_sydost": "Martin Linges vei sydøst",
    "rolfsbukt_syd": "Rolfsbuktveien syd",
}

# Appendix 1 from PGF Trafikkanalyse Snarøyveien, doc. 7133122.
# The original snv_nordost zone has been disaggregated into four zones to
# reflect the distinct E18/Ring 3 approaches already present in the network:
#   e18_vest (40%), e18_ost (35%), ring3_nord (15%), snv_nordost (10% local).
# Row and column totals are preserved (integer rounding, largest-remainder).
OD_MATRICES = {
    "4A": {
        "morning": {
            "snv_syd": [0, 1, 158, 138, 59, 39, 99, 21, 13, 110, 14],
            "bbv_west": [6, 0, 2, 2, 1, 1, 0, 3, 80, 13, 2],
            "e18_vest": [79, 1, 0, 0, 0, 0, 146, 14, 45, 178, 23],
            "e18_ost": [70, 1, 0, 0, 0, 0, 128, 12, 39, 156, 20],
            "ring3_nord": [30, 0, 0, 0, 0, 0, 55, 5, 17, 67, 9],
            "snv_nordost": [20, 0, 0, 0, 0, 0, 36, 3, 11, 45, 6],
            "wideroe_nordvest": [135, 1, 124, 108, 46, 31, 0, 23, 76, 303, 40],
            "odd_nansens_vest": [1, 0, 4, 3, 1, 1, 0, 0, 0, 1, 0],
            "snv_east": [2, 1, 6, 6, 2, 2, 4, 1, 0, 5, 1],
            "martin_linges_sydost": [9, 0, 18, 15, 7, 4, 11, 2, 1, 0, 8],
            "rolfsbukt_syd": [28, 0, 58, 51, 22, 14, 36, 8, 5, 16, 0],
        },
        "afternoon": {
            "snv_syd": [0, 1, 139, 121, 52, 35, 87, 18, 5, 23, 57],
            "bbv_west": [11, 0, 1, 0, 0, 0, 0, 1, 20, 2, 6],
            "e18_vest": [124, 2, 0, 0, 0, 0, 161, 10, 9, 28, 69],
            "e18_ost": [108, 2, 0, 0, 0, 0, 141, 8, 8, 24, 61],
            "ring3_nord": [46, 1, 0, 0, 0, 0, 60, 4, 4, 10, 26],
            "snv_nordost": [31, 0, 0, 0, 0, 0, 40, 2, 2, 7, 17],
            "wideroe_nordvest": [313, 5, 162, 141, 61, 40, 0, 24, 24, 70, 175],
            "odd_nansens_vest": [1, 0, 4, 3, 1, 1, 0, 0, 0, 0, 1],
            "snv_east": [17, 0, 103, 91, 39, 26, 65, 13, 0, 4, 10],
            "martin_linges_sydost": [55, 1, 121, 106, 46, 30, 76, 16, 4, 0, 47],
            "rolfsbukt_syd": [11, 0, 25, 22, 10, 6, 16, 3, 1, 8, 0],
        },
    },
    "1A": {
        "morning": {
            "snv_syd": [0, 1, 197, 172, 74, 49, 123, 26, 17, 137, 18],
            "bbv_west": [8, 0, 4, 3, 1, 1, 0, 5, 120, 19, 2],
            "e18_vest": [100, 1, 0, 0, 0, 0, 183, 17, 57, 224, 29],
            "e18_ost": [88, 1, 0, 0, 0, 0, 160, 15, 49, 196, 26],
            "ring3_nord": [37, 1, 0, 0, 0, 0, 69, 7, 21, 84, 11],
            "snv_nordost": [25, 0, 0, 0, 0, 0, 46, 4, 14, 56, 7],
            "wideroe_nordvest": [172, 2, 164, 144, 62, 41, 0, 29, 97, 386, 50],
            "odd_nansens_vest": [1, 0, 4, 4, 2, 1, 0, 0, 0, 2, 0],
            "snv_east": [2, 1, 6, 6, 2, 2, 4, 1, 0, 5, 1],
            "martin_linges_sydost": [9, 0, 18, 15, 7, 4, 11, 2, 1, 0, 8],
            "rolfsbukt_syd": [43, 0, 87, 77, 33, 22, 55, 11, 7, 24, 0],
        },
        "afternoon": {
            "snv_syd": [0, 1, 173, 152, 65, 43, 108, 23, 6, 28, 71],
            "bbv_west": [17, 0, 1, 1, 0, 0, 0, 1, 30, 4, 9],
            "e18_vest": [137, 2, 0, 0, 0, 0, 178, 11, 10, 30, 77],
            "e18_ost": [120, 2, 0, 0, 0, 0, 156, 9, 9, 27, 67],
            "ring3_nord": [52, 1, 0, 0, 0, 0, 67, 4, 4, 11, 29],
            "snv_nordost": [34, 0, 0, 0, 0, 0, 45, 3, 3, 8, 19],
            "wideroe_nordvest": [398, 6, 209, 182, 78, 52, 0, 31, 30, 89, 223],
            "odd_nansens_vest": [2, 0, 4, 4, 2, 1, 0, 0, 0, 0, 1],
            "snv_east": [17, 0, 103, 91, 39, 26, 65, 13, 0, 4, 10],
            "martin_linges_sydost": [55, 1, 121, 106, 46, 30, 76, 16, 4, 0, 47],
            "rolfsbukt_syd": [17, 0, 38, 33, 14, 10, 24, 5, 1, 11, 0],
        },
    },
}

# Base-network boundary edges selected to represent the OD zones from appendix 1.
ZONE_EDGE_CANDIDATES = {
    "snv_syd": {
        "origin": ["115505254"],
        "destination": ["115505232"],
    },
    "bbv_west": {
        "origin": ["-53141119"],
        "destination": ["53141119"],
    },
    "e18_vest": {
        "origin": ["1071762868"],
        "destination": ["113815194"],
    },
    "e18_ost": {
        "origin": ["13797031"],
        "destination": ["362382740"],
    },
    "ring3_nord": {
        "origin": ["131600897"],
        "destination": ["13797030"],
    },
    "snv_nordost": {
        "origin": ["466495271#0", "466495265#0"],
        "destination": ["313965530#1"],
    },
    "wideroe_nordvest": {
        "origin": ["32321958"],
        "destination": ["32321957"],
    },
    "odd_nansens_vest": {
        "origin": ["-53158894"],
        "destination": ["-1014336997"],
    },
    "snv_east": {
        "origin": ["-27194983"],
        "destination": ["27194983"],
    },
    "martin_linges_sydost": {
        "origin": ["-52975954"],
        "destination": ["52975954"],
    },
    "rolfsbukt_syd": {
        "origin": ["27184811#3"],
        "destination": ["-27184811#3"],
    },
}


def matrix_to_flows(matrix: dict[str, list[int]]) -> list[tuple[str, str, int]]:
    """Convert matrix rows into explicit OD flow tuples."""
    flows = []
    for from_zone, row in matrix.items():
        for to_zone, vehicles_per_hour in zip(ZONE_ORDER, row):
            if from_zone == to_zone or vehicles_per_hour <= 0:
                continue
            flows.append((from_zone, to_zone, vehicles_per_hour))
    return flows


def validate_zone_edges(net_file: Path) -> None:
    """Ensure all referenced candidate edges exist in the chosen network."""
    import sumolib

    net = sumolib.net.readNet(str(net_file))
    edge_ids = {edge.getID() for edge in net.getEdges()}
    missing = []
    for zone_name, zone_edges in ZONE_EDGE_CANDIDATES.items():
        for direction, candidates in zone_edges.items():
            for candidate in candidates:
                if candidate not in edge_ids:
                    missing.append((zone_name, direction, candidate))
    if missing:
        details = ", ".join(f"{zone}/{direction}:{edge}" for zone, direction, edge in missing)
        raise ValueError(f"Missing zone edge candidates in {net_file.name}: {details}")


def generate_od_csv(matrix: dict[str, list[int]], output_file: Path) -> None:
    """Write OD matrix as CSV for inspection."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    lines = ["from_zone,to_zone,vehicles_per_hour"]
    for from_zone, to_zone, vph in matrix_to_flows(matrix):
        lines.append(f"{from_zone},{to_zone},{vph}")
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OD matrix CSV -> {output_file}")


def generate_routes(
    net_file: Path,
    matrix: dict[str, list[int]],
    output_file: Path,
    seed: int = 42,
    period_start: int = 0,
    period_end: int = 3600,
    include_emergency: bool = True,
) -> int:
    """Generate SUMO trips from the appendix OD matrix.

    If include_emergency is True, adds 3 emergency vehicles at evenly spaced
    intervals during the peak hour.  They route from Snarøya (snv_syd) to
    nordre rundkjøring (snv_nordost), modelling an ambulance responding to a
    call on the peninsula.  SUMO's vClass="emergency" makes other vehicles
    yield (blue-light behaviour).
    """
    validate_zone_edges(net_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("routes")

    # --- passenger vehicle type ---
    vtype = ET.SubElement(root, "vType")
    vtype.set("id", "car")
    vtype.set("vClass", "passenger")
    vtype.set("length", "4.5")
    vtype.set("maxSpeed", "50.0")
    vtype.set("accel", "2.6")
    vtype.set("decel", "4.5")
    vtype.set("sigma", "0.5")
    vtype.set("jmTimegapMinor", "1.5")

    # --- emergency vehicle type (ambulance / blue-light) ---
    evtype = ET.SubElement(root, "vType")
    evtype.set("id", "emergency")
    evtype.set("vClass", "emergency")
    evtype.set("length", "6.5")
    evtype.set("maxSpeed", "38.89")       # ~140 km/h capability
    evtype.set("accel", "3.0")
    evtype.set("decel", "5.0")
    evtype.set("sigma", "0.0")            # no stochastic dawdling
    evtype.set("speedFactor", "1.0")
    evtype.set("jmDriveAfterRedTime", "3")  # can proceed through red
    evtype.set("jmIgnoreKeepClearTime", "3")
    evtype.set("color", "1,0,0")          # red in SUMO-GUI

    random.seed(seed)
    vehicles = []
    vehicle_id = 0

    for from_zone, to_zone, vehicles_per_hour in matrix_to_flows(matrix):
        origin_edges = ZONE_EDGE_CANDIDATES[from_zone]["origin"]
        destination_edges = ZONE_EDGE_CANDIDATES[to_zone]["destination"]
        interval = (period_end - period_start) / vehicles_per_hour

        for index in range(vehicles_per_hour):
            depart = period_start + index * interval + random.uniform(-interval * 0.3, interval * 0.3)
            depart = max(period_start, min(period_end - 1, depart))
            vehicles.append(
                (
                    depart,
                    vehicle_id,
                    random.choice(origin_edges),
                    random.choice(destination_edges),
                    from_zone,
                    to_zone,
                    "car",
                )
            )
            vehicle_id += 1

    # --- emergency vehicles (3 per peak hour) ---
    if include_emergency:
        EMERGENCY_COUNT = 3
        emergency_origin = ZONE_EDGE_CANDIDATES["snv_syd"]["origin"]
        emergency_dest = ZONE_EDGE_CANDIDATES["snv_nordost"]["destination"]
        spacing = (period_end - period_start) / (EMERGENCY_COUNT + 1)
        for i in range(EMERGENCY_COUNT):
            depart = period_start + spacing * (i + 1)
            vehicles.append(
                (
                    depart,
                    vehicle_id,
                    random.choice(emergency_origin),
                    random.choice(emergency_dest),
                    "snv_syd",
                    "snv_nordost",
                    "emergency",
                )
            )
            vehicle_id += 1

    vehicles.sort(key=lambda item: item[0])

    for depart, vid, from_edge, to_edge, from_zone, to_zone, vtype_id in vehicles:
        trip = ET.SubElement(root, "trip")
        trip.set("id", f"emer_{vid}" if vtype_id == "emergency" else f"veh_{vid}")
        trip.set("type", vtype_id)
        trip.set("depart", f"{depart:.1f}")
        trip.set("from", from_edge)
        trip.set("to", to_edge)
        trip.set("departLane", "best" if vtype_id == "car" else "free")
        trip.set("fromTaz", from_zone)
        trip.set("toTaz", to_zone)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(output_file), xml_declaration=True, encoding="utf-8")
    n_emer = sum(1 for v in vehicles if v[6] == "emergency")
    print(f"Route file ({len(vehicles)} vehicles, {n_emer} emergency) -> {output_file}")
    return len(vehicles)


def generate_event_overlay(
    net_file: Path,
    output_file: Path,
    seed: int = 42,
    attendees: int = 27500,
    car_share: float = 1 / 3,
    persons_per_car: float = 2.5,
    park_fraction: float = 1 / 3,
) -> int:
    """Generate a Unity Arena event-night demand overlay.

    The event overlay models concert traffic at Unity Arena (Telenor Arena):

    - **Inbound (sim time 1800-5400, i.e. 16:00-17:30):** Vehicles arrive
      from E18/nordre rundkjøring heading to the arena area (Snarøyveien øst
      zone). 1/3 park, 2/3 are drop-offs that leave immediately.
    - **Drop-off outbound:** Vehicles that dropped off return toward E18
      immediately.

    The PM simulation window is 15:30-17:00 (5400s total).  Event arrival
    starts at 16:00 (sim time 1800s), so 1 hour of event inbound traffic
    overlaps.  This captures the critical compounding of commuter PM peak
    with early event arrivals.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total_cars = int(attendees * car_share / persons_per_car)
    park_cars = int(total_cars * park_fraction)
    dropoff_cars = total_cars - park_cars

    # Inbound: all cars arrive sim time 1800-5400 (16:00-17:30)
    # The distribution front-loads slightly (most arrive 16:00-17:00)
    EVENT_START = 1800  # sim seconds = 16:00
    EVENT_END = 5400    # sim seconds = 17:30

    random.seed(seed + 1000)  # different seed from main demand

    # Edges: inbound from nordre rundkjøring, destination near Unity Arena
    # Unity Arena is near the snv_east / martin_linges zone
    inbound_origins = ZONE_EDGE_CANDIDATES["snv_nordost"]["origin"]
    arena_dest = ZONE_EDGE_CANDIDATES["snv_east"]["destination"]
    outbound_dest = ZONE_EDGE_CANDIDATES["snv_nordost"]["destination"]

    root = ET.Element("routes")

    # Reuse the car vType from main demand (same route file will be merged)
    vtype = ET.SubElement(root, "vType")
    vtype.set("id", "event_car")
    vtype.set("vClass", "passenger")
    vtype.set("length", "4.5")
    vtype.set("maxSpeed", "50.0")
    vtype.set("accel", "2.6")
    vtype.set("decel", "4.5")
    vtype.set("sigma", "0.5")
    vtype.set("color", "0.2,0.2,0.8")  # blue tint for event cars

    vehicles = []
    vid = 0

    # Inbound arrivals (distributed over EVENT_START to EVENT_END)
    for i in range(total_cars):
        # Front-loaded distribution: beta distribution skewed early
        t = EVENT_START + random.betavariate(2, 3) * (EVENT_END - EVENT_START)
        vehicles.append((
            t, vid,
            random.choice(inbound_origins),
            random.choice(arena_dest),
            "snv_nordost", "snv_east", "event_car",
        ))
        vid += 1

    # Drop-off vehicles leave ~2-5 minutes after arriving
    for i in range(dropoff_cars):
        base_arrival = EVENT_START + random.betavariate(2, 3) * (EVENT_END - EVENT_START)
        depart = base_arrival + random.uniform(120, 300)  # 2-5 min turnaround
        if depart < EVENT_END + 600:  # allow some overflow
            vehicles.append((
                depart, vid,
                random.choice(ZONE_EDGE_CANDIDATES["snv_east"]["origin"]),
                random.choice(outbound_dest),
                "snv_east", "snv_nordost", "event_car",
            ))
            vid += 1

    vehicles.sort(key=lambda v: v[0])

    for depart, v_id, from_edge, to_edge, from_zone, to_zone, vtype_id in vehicles:
        trip = ET.SubElement(root, "trip")
        trip.set("id", f"event_{v_id}")
        trip.set("type", vtype_id)
        trip.set("depart", f"{depart:.1f}")
        trip.set("from", from_edge)
        trip.set("to", to_edge)
        trip.set("departLane", "best")
        trip.set("fromTaz", from_zone)
        trip.set("toTaz", to_zone)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(output_file), xml_declaration=True, encoding="utf-8")

    n_inbound = total_cars
    n_dropoff_out = sum(1 for v in vehicles if v[6] == "event_car") - total_cars
    print(
        f"Event overlay ({n_inbound} inbound + {n_dropoff_out} drop-off outbound"
        f" = {len(vehicles)} total vehicles) -> {output_file}"
    )
    return len(vehicles)


def generate_all_demand() -> None:
    """Generate OD CSVs and route files for both scenarios and both peak hours."""
    print("=" * 60)
    print("PHASE 2: Generating traffic demand from appendix OD matrices")
    print("=" * 60)

    routes_dir = DEMAND_DIR / "routes"
    od_dir = DEMAND_DIR / "od_matrices"
    base_net = PROJECT_ROOT / "network" / "base" / "fornebu.net.xml"

    for scenario_name, periods in OD_MATRICES.items():
        for period_name, matrix in periods.items():
            suffix = f"{period_name}_{scenario_name}"
            generate_od_csv(matrix, od_dir / f"{suffix}.csv")
            generate_routes(
                base_net,
                matrix,
                routes_dir / f"{suffix}.rou.xml",
                seed=42,
            )

    # Generate Unity Arena event overlay
    print("\nGenerating Unity Arena event-night overlay...")
    generate_event_overlay(
        base_net,
        routes_dir / "event_overlay.rou.xml",
    )

    print("\nGenerated OD files for:")
    for zone_id, zone_label in ZONE_LABELS.items():
        print(f"  {zone_id}: {zone_label}")
    print("\nAll demand files generated.")


if __name__ == "__main__":
    generate_all_demand()
