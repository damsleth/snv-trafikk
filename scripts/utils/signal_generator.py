#!/usr/bin/env python3
"""Generate traffic signal plans for Bernt Balchens vei crossing (Lyskrysset)."""

import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SIGNALS_DIR = PROJECT_ROOT / "network" / "signals"


def generate_signal_plan(
    junction_id: str,
    output_file: Path = None,
    cycle_time: int = 90,
    nb_green: int = 35,
    sb_green: int = 25,
    ped_green: int = 15,
    yellow: int = 3,
    all_red: int = 2,
):
    """Generate a fixed-time signal plan for Bernt Balchens vei crossing.

    Phases:
    1. Northbound + Southbound through (main green)
    2. Southbound left turn to Bernt Balchens vei
    3. Pedestrian crossing phase
    4. All-red clearance

    Args:
        junction_id: SUMO junction ID for the signal
        output_file: Output .add.xml file path
        cycle_time: Total cycle time in seconds
        nb_green: Green time for northbound through
        sb_green: Green time for southbound + left turn
        ped_green: Green time for pedestrian phase
        yellow: Yellow time
        all_red: All-red clearance time
    """
    if output_file is None:
        output_file = SIGNALS_DIR / "bernt_balchens.add.xml"

    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    # Build the additional file
    root = ET.Element("additional")

    tl = ET.SubElement(root, "tlLogic")
    tl.set("id", junction_id)
    tl.set("type", "static")
    tl.set("programID", "custom")
    tl.set("offset", "0")

    # Phase 1: Main through traffic (N-S green, E-W red, peds red)
    # State string: each char = one signal group
    # G=green, g=green-minor, y=yellow, r=red
    # For a typical 4-arm intersection with 8 signal groups (2 per arm):
    # Groups: N-through, N-left, S-through, S-left, E-through, E-left, W-through, W-left, Ped-NS, Ped-EW

    # Simplified: we model as N/S mainline + E/W side street + pedestrians
    # Phase states assume this link order (will be adjusted based on actual junction):
    # Links: 0-N_through, 1-N_left, 2-S_through, 3-S_left, 4-E_through, 5-E_left, 6-Ped

    # Phase 1: North-South through movement
    phase1 = ET.SubElement(tl, "phase")
    phase1.set("duration", str(nb_green))
    phase1.set("state", "GGGGrrrrr")  # N/S green, E/W red, ped red

    # Yellow transition
    phase_y1 = ET.SubElement(tl, "phase")
    phase_y1.set("duration", str(yellow))
    phase_y1.set("state", "yyyyrrrrr")

    # All red
    phase_ar1 = ET.SubElement(tl, "phase")
    phase_ar1.set("duration", str(all_red))
    phase_ar1.set("state", "rrrrrrrrr")

    # Phase 2: East-West (Bernt Balchens vei) movement
    phase2 = ET.SubElement(tl, "phase")
    phase2.set("duration", str(sb_green))
    phase2.set("state", "rrrrGGrrr")  # E/W green

    # Yellow
    phase_y2 = ET.SubElement(tl, "phase")
    phase_y2.set("duration", str(yellow))
    phase_y2.set("state", "rrrryyrrr")

    # All red
    phase_ar2 = ET.SubElement(tl, "phase")
    phase_ar2.set("duration", str(all_red))
    phase_ar2.set("state", "rrrrrrrrr")

    # Phase 3: Pedestrian crossing
    phase3 = ET.SubElement(tl, "phase")
    phase3.set("duration", str(ped_green))
    phase3.set("state", "rrrrrrGGG")  # Peds green

    # Yellow/clearance for peds
    phase_y3 = ET.SubElement(tl, "phase")
    phase_y3.set("duration", str(yellow))
    phase_y3.set("state", "rrrrrrrrr")

    # All red before restart
    phase_ar3 = ET.SubElement(tl, "phase")
    phase_ar3.set("duration", str(all_red))
    phase_ar3.set("state", "rrrrrrrrr")

    # Write
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(output_file), xml_declaration=True, encoding="utf-8")
    print(f"Signal plan written → {output_file}")
    return output_file


def generate_optimized_signal_plan(junction_id: str, output_file: Path = None):
    """Generate an optimized signal plan with longer green for main direction."""
    if output_file is None:
        output_file = SIGNALS_DIR / "bernt_balchens_optimized.add.xml"

    return generate_signal_plan(
        junction_id=junction_id,
        output_file=output_file,
        cycle_time=120,
        nb_green=50,  # More green for main direction
        sb_green=30,
        ped_green=12,  # Slightly shorter ped phase
        yellow=3,
        all_red=2,
    )


if __name__ == "__main__":
    # Default junction ID — will be updated after network is built
    generate_signal_plan("lyskrysset")
    generate_optimized_signal_plan("lyskrysset")
