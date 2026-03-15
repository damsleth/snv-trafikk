#!/usr/bin/env python3
"""Generate traffic demand from OD matrices based on PGF traffic analysis.

Creates SUMO route files (.rou.xml) for each scenario/time period combination.
Traffic volumes from PGF Trafikkanalyse (doc 7133122), Scenario 4A, year 2040.
"""

import random
import xml.etree.ElementTree as ET
from pathlib import Path

import sumolib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NETWORK_DIR = PROJECT_ROOT / "network"
DEMAND_DIR = PROJECT_ROOT / "demand"
BASE_NET = NETWORK_DIR / "base" / "fornebu.net.xml"

# ============================================================================
# TURNING MOVEMENT DATA from PGF Analysis
# Scenario 4A, Year 2040, Peak Hours
# ============================================================================

# Morning rush 07:45-08:45
MORNING_4A = {
    "nordre_rundkjoring": {
        # From → To: vehicles/hour
        ("snv_nord", "southbound"): 850,      # Snarøyveien nord → southbound
        ("snv_nord", "wideroev"): 365,         # Snarøyveien nord → Widerøeveien
        ("wideroev", "snv_nord"): 310,         # Widerøeveien → Snarøyveien nord
        ("wideroev", "southbound"): 580,       # Widerøeveien → southbound (via rundkjøring)
        ("southbound", "snv_nord"): 150,       # Southbound → Snarøyveien nord
        ("southbound", "wideroev"): 615,       # Southbound → Widerøeveien
    },
    "sondre_rundkjoring": {
        ("snv_sor", "northbound"): 650,        # Snarøya → northbound
        ("snv_sor", "rolfsbuktv"): 35,         # Snarøya → Rolfsbuktveien
        ("rolfsbuktv", "northbound"): 125,     # Rolfsbuktveien → northbound
        ("northbound", "snv_sor"): 285,        # Northbound → Snarøya
        ("northbound", "rolfsbuktv"): 250,     # Northbound → Rolfsbuktveien
    },
}

# Afternoon rush 15:30-16:30 (scaled from plan documents — reverse dominant direction)
AFTERNOON_4A = {
    "nordre_rundkjoring": {
        ("snv_nord", "southbound"): 605,
        ("snv_nord", "wideroev"): 450,
        ("wideroev", "snv_nord"): 275,
        ("wideroev", "southbound"): 680,
        ("southbound", "snv_nord"): 200,
        ("southbound", "wideroev"): 780,
    },
    "sondre_rundkjoring": {
        ("snv_sor", "northbound"): 535,
        ("snv_sor", "rolfsbuktv"): 25,
        ("rolfsbuktv", "northbound"): 80,
        ("northbound", "snv_sor"): 450,
        ("northbound", "rolfsbuktv"): 285,
    },
}

# Scenario 1A scaling factor (42,400 / 31,300 ≈ 1.355)
SCENARIO_1A_FACTOR = 42400.0 / 31300.0


def find_edges_by_area(net) -> dict:
    """Map zone names to edge IDs in the network.

    Zones:
    - snv_nord: Snarøyveien north of nordre rundkjøring (towards E18)
    - snv_sor: Snarøyveien south of søndre rundkjøring (Snarøya)
    - wideroev: Widerøeveien
    - rolfsbuktv: Rolfsbuktveien
    - southbound: Snarøyveien between roundabouts, southbound
    - northbound: Snarøyveien between roundabouts, northbound
    """
    # Y-coordinate thresholds based on actual network layout:
    # - Nordre rundkjøring (Widerøeveien) ≈ y=2900
    # - Søndre rundkjøring (Rolfsbuktveien) ≈ y=1800
    NORDRE_Y = 2900
    SONDRE_Y = 1800

    zones = {
        "snv_nord": [],      # Snarøyveien north of nordre rundkjøring (E18 direction)
        "snv_sor": [],       # Snarøyveien south of søndre rundkjøring (Snarøya)
        "wideroev": [],      # Widerøeveien
        "rolfsbuktv": [],    # Rolfsbuktveien
        "northbound": [],    # Snarøyveien between roundabouts, northbound
        "southbound": [],    # Snarøyveien between roundabouts, southbound
    }

    for edge in net.getEdges():
        eid = edge.getID()
        if eid.startswith(":"):
            continue
        name = (edge.getName() or "").lower()
        from_y = edge.getFromNode().getCoord()[1]
        to_y = edge.getToNode().getCoord()[1]
        mid_y = (from_y + to_y) / 2

        if "widerøe" in name or "wideroe" in name:
            zones["wideroev"].append(eid)
        elif "rolfsbuk" in name:
            zones["rolfsbuktv"].append(eid)
        elif "snarøyveien" in name or "snaroyveien" in name:
            is_nb = to_y > from_y

            if mid_y > NORDRE_Y:
                # North of nordre rundkjøring → snv_nord zone
                zones["snv_nord"].append(eid)
            elif mid_y < SONDRE_Y:
                # South of søndre rundkjøring → snv_sor zone (Snarøya)
                zones["snv_sor"].append(eid)
            else:
                # Between the two roundabouts
                if is_nb:
                    zones["northbound"].append(eid)
                else:
                    zones["southbound"].append(eid)

    # Also add E18/Drammensveien boundary edges as alternative snv_nord destinations
    for edge in net.getEdges():
        eid = edge.getID()
        if eid.startswith(":"):
            continue
        name = (edge.getName() or "").lower()
        if "drammensveien" in name or "lysaker" in name:
            # These serve as E18 connection points
            if eid not in zones["snv_nord"]:
                zones["snv_nord"].append(eid)

    # Debug output
    for zone, edges in zones.items():
        print(f"  Zone '{zone}': {len(edges)} edges")

    return zones


def generate_od_csv(flows: dict, output_file: Path, period: str):
    """Write OD matrix as CSV for reference."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write("intersection,from,to,vehicles_per_hour\n")
        for intersection, movements in flows.items():
            for (from_zone, to_zone), vph in movements.items():
                f.write(f"{intersection},{from_zone},{to_zone},{vph}\n")
    print(f"OD matrix CSV → {output_file}")


def generate_routes(
    net_file: Path,
    flows: dict,
    output_file: Path,
    period_start: int = 0,
    period_end: int = 3600,
    seed: int = 42,
    scale: float = 1.0,
):
    """Generate SUMO route file from turning movement data.

    Uses flow definitions that SUMO's jtrrouter or duarouter can process.
    For simplicity, we generate explicit vehicle departures with routes.
    """
    net = sumolib.net.readNet(str(net_file))
    zones = find_edges_by_area(net)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Build route file with flows
    root = ET.Element("routes")

    # Vehicle type
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
    veh_id = 0
    all_vehicles = []

    # Flatten all flows from all intersections
    all_flows = {}
    for intersection, movements in flows.items():
        for (from_zone, to_zone), vph in movements.items():
            key = (from_zone, to_zone)
            all_flows[key] = all_flows.get(key, 0) + vph

    # For each OD pair, find route and generate vehicles
    for (from_zone, to_zone), vph in all_flows.items():
        from_edges = zones.get(from_zone, [])
        to_edges = zones.get(to_zone, [])

        if not from_edges or not to_edges:
            print(f"  WARNING: No edges for {from_zone} → {to_zone}, skipping {vph} veh/h")
            continue

        scaled_vph = int(vph * scale)

        # Generate Poisson-distributed departures
        interval = (period_end - period_start) / max(scaled_vph, 1)

        for i in range(scaled_vph):
            # Add some randomness to departure time
            depart = period_start + i * interval + random.uniform(-interval * 0.3, interval * 0.3)
            depart = max(period_start, min(period_end - 1, depart))

            from_edge = random.choice(from_edges)
            to_edge = random.choice(to_edges)

            if from_edge == to_edge:
                continue

            all_vehicles.append((depart, veh_id, from_edge, to_edge))
            veh_id += 1

    # Sort by departure time
    all_vehicles.sort(key=lambda x: x[0])

    # Write vehicles as trips (SUMO will route them)
    for depart, vid, from_edge, to_edge in all_vehicles:
        trip = ET.SubElement(root, "trip")
        trip.set("id", f"veh_{vid}")
        trip.set("type", "car")
        trip.set("depart", f"{depart:.1f}")
        trip.set("from", from_edge)
        trip.set("to", to_edge)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(output_file), xml_declaration=True, encoding="utf-8")
    print(f"Route file ({len(all_vehicles)} vehicles) → {output_file}")
    return len(all_vehicles)


def generate_all_demand():
    """Generate demand files for all scenarios."""
    print("=" * 60)
    print("PHASE 2: Generating traffic demand")
    print("=" * 60)

    if not BASE_NET.exists():
        print(f"ERROR: Base network not found at {BASE_NET}")
        print("Run scripts/02_build_network.py first.")
        return

    routes_dir = DEMAND_DIR / "routes"
    od_dir = DEMAND_DIR / "od_matrices"

    # Generate OD CSV files for reference
    generate_od_csv(MORNING_4A, od_dir / "morning_4A.csv", "morning")
    generate_od_csv(AFTERNOON_4A, od_dir / "afternoon_4A.csv", "afternoon")

    # Scale 1A
    morning_1a = {}
    for inter, movements in MORNING_4A.items():
        morning_1a[inter] = {k: int(v * SCENARIO_1A_FACTOR) for k, v in movements.items()}
    afternoon_1a = {}
    for inter, movements in AFTERNOON_4A.items():
        afternoon_1a[inter] = {k: int(v * SCENARIO_1A_FACTOR) for k, v in movements.items()}

    generate_od_csv(morning_1a, od_dir / "morning_1A.csv", "morning")
    generate_od_csv(afternoon_1a, od_dir / "afternoon_1A.csv", "afternoon")

    # Generate route files
    # Scenario 4A morning (main scenario)
    print("\nGenerating Scenario 4A morning routes...")
    generate_routes(
        BASE_NET, MORNING_4A,
        routes_dir / "morning_4A.rou.xml",
        period_start=0, period_end=3600,
    )

    # Scenario 4A afternoon
    print("Generating Scenario 4A afternoon routes...")
    generate_routes(
        BASE_NET, AFTERNOON_4A,
        routes_dir / "afternoon_4A.rou.xml",
        period_start=0, period_end=3600,
    )

    # Scenario 1A morning (higher demand)
    print("Generating Scenario 1A morning routes...")
    generate_routes(
        BASE_NET, MORNING_4A,
        routes_dir / "morning_1A.rou.xml",
        period_start=0, period_end=3600,
        scale=SCENARIO_1A_FACTOR,
    )

    # Scenario 1A afternoon
    print("Generating Scenario 1A afternoon routes...")
    generate_routes(
        BASE_NET, AFTERNOON_4A,
        routes_dir / "afternoon_1A.rou.xml",
        period_start=0, period_end=3600,
        scale=SCENARIO_1A_FACTOR,
    )

    print("\n✓ All demand files generated!")


if __name__ == "__main__":
    generate_all_demand()
