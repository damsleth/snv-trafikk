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
    "snv_nordost": "Snarøyveien nordost",
    "wideroe_nordvest": "Widerøeveien nordvest",
    "odd_nansens_vest": "Odd Nansens vei vest",
    "snv_east": "Snarøyveien øst",
    "martin_linges_sydost": "Martin Linges vei sydøst",
    "rolfsbukt_syd": "Rolfsbuktveien syd",
}

# Appendix 1 from PGF Trafikkanalyse Snarøyveien, doc. 7133122.
OD_MATRICES = {
    "4A": {
        "morning": {
            "snv_syd": [0, 1, 394, 99, 21, 13, 110, 14],
            "bbv_west": [6, 0, 6, 0, 3, 80, 13, 2],
            "snv_nordost": [199, 2, 0, 365, 34, 112, 446, 58],
            "wideroe_nordvest": [135, 1, 309, 0, 23, 76, 303, 40],
            "odd_nansens_vest": [1, 0, 9, 0, 0, 0, 1, 0],
            "snv_east": [2, 1, 16, 4, 1, 0, 5, 1],
            "martin_linges_sydost": [9, 0, 44, 11, 2, 1, 0, 8],
            "rolfsbukt_syd": [28, 0, 145, 36, 8, 5, 16, 0],
        },
        "afternoon": {
            "snv_syd": [0, 1, 347, 87, 18, 5, 23, 57],
            "bbv_west": [11, 0, 1, 0, 1, 20, 2, 6],
            "snv_nordost": [309, 5, 0, 402, 24, 23, 69, 173],
            "wideroe_nordvest": [313, 5, 404, 0, 24, 24, 70, 175],
            "odd_nansens_vest": [1, 0, 9, 0, 0, 0, 0, 1],
            "snv_east": [17, 0, 259, 65, 13, 0, 4, 10],
            "martin_linges_sydost": [55, 1, 303, 76, 16, 4, 0, 47],
            "rolfsbukt_syd": [11, 0, 63, 16, 3, 1, 8, 0],
        },
    },
    "1A": {
        "morning": {
            "snv_syd": [0, 1, 492, 123, 26, 17, 137, 18],
            "bbv_west": [8, 0, 9, 0, 5, 120, 19, 2],
            "snv_nordost": [250, 3, 0, 458, 43, 141, 560, 73],
            "wideroe_nordvest": [172, 2, 411, 0, 29, 97, 386, 50],
            "odd_nansens_vest": [1, 0, 11, 0, 0, 0, 2, 0],
            "snv_east": [2, 1, 16, 4, 1, 0, 5, 1],
            "martin_linges_sydost": [9, 0, 44, 11, 2, 1, 0, 8],
            "rolfsbukt_syd": [43, 0, 219, 55, 11, 7, 24, 0],
        },
        "afternoon": {
            "snv_syd": [0, 1, 433, 108, 23, 6, 28, 71],
            "bbv_west": [17, 0, 2, 0, 1, 30, 4, 9],
            "snv_nordost": [343, 5, 0, 446, 27, 26, 76, 192],
            "wideroe_nordvest": [398, 6, 521, 0, 31, 30, 89, 223],
            "odd_nansens_vest": [2, 0, 11, 0, 0, 0, 0, 1],
            "snv_east": [17, 0, 259, 65, 13, 0, 4, 10],
            "martin_linges_sydost": [55, 1, 303, 76, 16, 4, 0, 47],
            "rolfsbukt_syd": [17, 0, 95, 24, 5, 1, 11, 0],
        },
    },
}

# Base-network boundary edges selected to represent the OD zones from appendix 1.
ZONE_EDGE_CANDIDATES = {
    "snv_syd": {
        "origin": ["515410724#0"],
        "destination": ["1077838551#1"],
    },
    "bbv_west": {
        "origin": ["-53141119"],
        "destination": ["53141119"],
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
) -> int:
    """Generate SUMO trips from the appendix OD matrix."""
    validate_zone_edges(net_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("routes")
    vtype = ET.SubElement(root, "vType")
    vtype.set("id", "car")
    vtype.set("vClass", "passenger")
    vtype.set("length", "4.5")
    vtype.set("maxSpeed", "50.0")
    vtype.set("accel", "2.6")
    vtype.set("decel", "4.5")
    vtype.set("sigma", "0.5")
    vtype.set("jmTimegapMinor", "1.5")

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
                )
            )
            vehicle_id += 1

    vehicles.sort(key=lambda item: item[0])

    for depart, vid, from_edge, to_edge, from_zone, to_zone in vehicles:
        trip = ET.SubElement(root, "trip")
        trip.set("id", f"veh_{vid}")
        trip.set("type", "car")
        trip.set("depart", f"{depart:.1f}")
        trip.set("from", from_edge)
        trip.set("to", to_edge)
        trip.set("departLane", "best")
        trip.set("fromTaz", from_zone)
        trip.set("toTaz", to_zone)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(output_file), xml_declaration=True, encoding="utf-8")
    print(f"Route file ({len(vehicles)} vehicles) -> {output_file}")
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

    print("\nGenerated OD files for:")
    for zone_id, zone_label in ZONE_LABELS.items():
        print(f"  {zone_id}: {zone_label}")
    print("\nAll demand files generated.")


if __name__ == "__main__":
    generate_all_demand()
