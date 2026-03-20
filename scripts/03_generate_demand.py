#!/usr/bin/env python3
"""Generate SUMO demand from the OD matrices in PGF appendix 1.

The official traffic analysis provides full OD matrices for scenario 1A/4A and
both peak hours. This script encodes those matrices directly instead of
flattening intersection turning counts into unrelated trips.
"""

import argparse
import random
import xml.etree.ElementTree as ET
from math import floor
from pathlib import Path

from utils.scenario_catalog import declared_demand_variants, demand_route_path, format_demand_scale


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

OFFICIAL_ZONE_ORDER = [
    "snv_syd",
    "bbv_west",
    "snv_nordost",
    "wideroe_nordvest",
    "odd_nansens_vest",
    "snv_east",
    "martin_linges_sydost",
    "rolfsbukt_syd",
]

# Appendix 1 from PGF Trafikkanalyse Snarøyveien, doc. 7133122.
# These are the published 8-zone Aimsun matrices transcribed directly from the
# appendix pages. The north-east gateway zone ("3.1 Snarøyveien NORDØST") is
# disaggregated below into the four network-specific approach zones used by
# this SUMO model.
OFFICIAL_OD_MATRICES = {
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

NORDOST_SPLIT_WEIGHTS = {
    "e18_vest": 0.40,
    "e18_ost": 0.35,
    "ring3_nord": 0.15,
    "snv_nordost": 0.10,
}


def split_count(total: int, weights: dict[str, float]) -> dict[str, int]:
    """Split an integer total by weights while preserving the exact total."""
    allocated = {}
    remainders = []
    floor_total = 0

    for zone_name, weight in weights.items():
        raw = total * weight
        base = floor(raw)
        allocated[zone_name] = base
        floor_total += base
        remainders.append((raw - base, zone_name))

    for _, zone_name in sorted(remainders, key=lambda item: item[0], reverse=True)[: total - floor_total]:
        allocated[zone_name] += 1

    return allocated


def disaggregate_official_matrix(matrix: dict[str, list[int]]) -> dict[str, list[int]]:
    """Expand the appendix 8-zone matrix to the 11-zone network representation."""
    expanded = {zone_name: [0] * len(ZONE_ORDER) for zone_name in ZONE_ORDER}

    for from_zone, row in matrix.items():
        for to_zone, vehicle_count in zip(OFFICIAL_ZONE_ORDER, row):
            if vehicle_count <= 0:
                continue

            if from_zone == "snv_nordost" and to_zone == "snv_nordost":
                raise ValueError("Expected appendix nordost->nordost cell to stay empty")

            if from_zone == "snv_nordost":
                split_rows = split_count(vehicle_count, NORDOST_SPLIT_WEIGHTS)
                for split_zone, split_value in split_rows.items():
                    expanded[split_zone][ZONE_ORDER.index(to_zone)] = split_value
                continue

            if to_zone == "snv_nordost":
                split_columns = split_count(vehicle_count, NORDOST_SPLIT_WEIGHTS)
                for split_zone, split_value in split_columns.items():
                    expanded[from_zone][ZONE_ORDER.index(split_zone)] = split_value
                continue

            expanded[from_zone][ZONE_ORDER.index(to_zone)] = vehicle_count

    return expanded


OD_MATRICES = {
    demand_name: {
        period_name: disaggregate_official_matrix(matrix)
        for period_name, matrix in periods.items()
    }
    for demand_name, periods in OFFICIAL_OD_MATRICES.items()
}

# Base-network boundary edges selected to represent the OD zones from appendix 1.
ZONE_EDGE_CANDIDATES = {
    "snv_syd": {
        "origin": ["-27195187#3"],
        "destination": ["27195187#2"],
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


def round_half_up(value: float) -> int:
    return int(value + 0.5)


def scale_matrix(matrix: dict[str, list[int]], demand_scale: float) -> dict[str, list[int]]:
    """Scale an OD matrix while preserving the rounded total via largest remainder."""
    if demand_scale <= 0:
        raise ValueError("demand_scale must be positive")

    if demand_scale == 1.0:
        return {zone: list(row) for zone, row in matrix.items()}

    scaled_matrix = {zone: [0] * len(row) for zone, row in matrix.items()}
    remainders: list[tuple[float, str, int]] = []
    total_floor = 0
    total_raw = 0.0

    for from_zone, row in matrix.items():
        for column_index, vehicles_per_hour in enumerate(row):
            if vehicles_per_hour <= 0:
                continue
            scaled_value = vehicles_per_hour * demand_scale
            base_value = floor(scaled_value)
            scaled_matrix[from_zone][column_index] = base_value
            total_floor += base_value
            total_raw += scaled_value
            remainders.append((scaled_value - base_value, from_zone, column_index))

    target_total = round_half_up(total_raw)
    additional_vehicles = max(target_total - total_floor, 0)
    for _, from_zone, column_index in sorted(remainders, key=lambda item: item[0], reverse=True)[:additional_vehicles]:
        scaled_matrix[from_zone][column_index] += 1

    return scaled_matrix


def resolve_demand_variants(extra_scales: list[float] | None = None) -> dict[str, list[float]]:
    """Resolve which demand scales should be emitted for each declared demand profile."""
    variants = {demand_name: {1.0} for demand_name in OD_MATRICES}

    for demand_name, demand_scale in declared_demand_variants():
        if demand_name in variants:
            variants[demand_name].add(demand_scale)

    for demand_scale in extra_scales or []:
        if demand_scale <= 0:
            raise ValueError("demand_scale must be positive")
        for demand_name in variants:
            variants[demand_name].add(float(demand_scale))

    return {
        demand_name: sorted(demand_scales)
        for demand_name, demand_scales in variants.items()
    }


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

    - **Inbound (sim time 1800-3600, i.e. 16:00-16:30):** Vehicles arrive
      from E18/nordre rundkjøring heading to the arena area (Snarøyveien øst
      zone). 1/3 park, 2/3 are drop-offs that leave immediately.
    - **Drop-off outbound:** Vehicles that dropped off return toward E18
      immediately.

    The PM simulation window follows the report's peak-hour period
    15:30-16:30 (3600s total). Event arrival starts at 16:00 (sim time 1800s),
    so the overlay captures the first 30 minutes where commuter PM peak and
    event arrivals overlap.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total_cars = int(attendees * car_share / persons_per_car)
    park_cars = int(total_cars * park_fraction)
    dropoff_cars = total_cars - park_cars

    # Inbound: all cars arrive sim time 1800-3600 (16:00-16:30)
    EVENT_START = 1800  # sim seconds = 16:00
    EVENT_END = 3600    # sim seconds = 16:30

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


def generate_all_demand(demand_scales: list[float] | None = None) -> None:
    """Generate OD CSVs and route files for the declared demand profiles and scales."""
    print("=" * 60)
    print("PHASE 2: Generating traffic demand from appendix OD matrices")
    print("=" * 60)

    routes_dir = DEMAND_DIR / "routes"
    od_dir = DEMAND_DIR / "od_matrices"
    base_net = PROJECT_ROOT / "network" / "base" / "fornebu.net.xml"
    demand_variants = resolve_demand_variants(demand_scales)

    print("Demand scales:")
    for demand_name, scales in demand_variants.items():
        labels = ", ".join(format_demand_scale(scale) for scale in scales)
        print(f"  {demand_name}: {labels}x")

    for scenario_name, periods in OD_MATRICES.items():
        for period_name, matrix in periods.items():
            for demand_scale in demand_variants[scenario_name]:
                scaled_matrix = scale_matrix(matrix, demand_scale)
                route_path = demand_route_path(period_name, scenario_name, demand_scale)
                suffix = route_path.stem.replace(".rou", "")
                generate_od_csv(scaled_matrix, od_dir / f"{suffix}.csv")
                generate_routes(
                    base_net,
                    scaled_matrix,
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
    try:
        parser = argparse.ArgumentParser(description="Generate SUMO demand from PGF OD matrices")
        parser.add_argument(
            "--demand-scale",
            action="append",
            type=float,
            default=[],
            help="Generate additional scaled demand variants (for example 0.8 for 80%% demand). May be repeated.",
        )
        args = parser.parse_args()
        generate_all_demand(demand_scales=args.demand_scale)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
