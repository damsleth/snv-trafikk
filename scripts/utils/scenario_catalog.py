#!/usr/bin/env python3
"""Shared scenario metadata for simulation, analysis, and reporting."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NETWORK_DIR = PROJECT_ROOT / "network"
DEMAND_DIR = PROJECT_ROOT / "demand"

PERIODS = {
    "morning": {
        "route_suffix": "morning",
        "label": "AM",
        "title": "morgenrush 07:45-08:45",
    },
    "afternoon": {
        "route_suffix": "afternoon",
        "label": "PM",
        "title": "ettermiddagsrush 15:30-16:30",
    },
}

SCENARIO_FAMILIES = {
    "scenario_4A_base": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "demand": "4A",
        "label": "Base (dagens profil)",
        "color": "#2ecc71",
        "description": "Scenario 4A demand on current network",
    },
    "scenario_4A_v1": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "label": "V1",
        "color": "#e74c3c",
        "description": "Scenario 4A on official V1 lane layout",
    },
    "scenario_4A_v2": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v2.net.xml",
        "demand": "4A",
        "label": "V2",
        "color": "#e67e22",
        "description": "Scenario 4A on official V2 lane layout",
    },
    "scenario_4A_v3": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v3.net.xml",
        "demand": "4A",
        "label": "V3",
        "color": "#8e44ad",
        "description": "Scenario 4A on official V3 lane layout",
    },
    "scenario_1A_base": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "demand": "1A",
        "label": "Base (Sc. 1A)",
        "color": "#16a085",
        "description": "Scenario 1A demand on current network",
    },
    "scenario_1A_v1": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "1A",
        "label": "V1 (Sc. 1A)",
        "color": "#c0392b",
        "description": "Scenario 1A demand on official V1 lane layout",
    },
    "scenario_4A_v1_rolfsbukt": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "label": "V1 + miljøgate",
        "color": "#d35400",
        "description": "V1 lane layout with Rolfsbuktveien miljøgate (15 km/h)",
        "extra_additional": [
            str(NETWORK_DIR / "signals" / "rolfsbukt_miljogate.add.xml"),
        ],
    },
}


def build_scenarios() -> dict:
    """Expand families into per-period scenarios."""
    scenarios = {}
    for family_name, family in SCENARIO_FAMILIES.items():
        for period_name, period in PERIODS.items():
            scenario_name = f"{family_name}_{period_name}"
            additional = [
                str(NETWORK_DIR / "signals" / "roundabout_params.add.xml"),
            ] + family.get("extra_additional", [])
            scenarios[scenario_name] = {
                "family": family_name,
                "period": period_name,
                "network": family["network"],
                "routes": DEMAND_DIR / "routes" / f"{period['route_suffix']}_{family['demand']}.rou.xml",
                "description": f"{family['description']} ({period_name})",
                "label": f"{family['label']} {period['label']}",
                "color": family["color"],
                "additional": additional,
            }
    return scenarios


SCENARIOS = build_scenarios()


def scenario_family(name: str) -> str:
    if name.endswith("_morning"):
        return name[:-8]
    if name.endswith("_afternoon"):
        return name[:-10]
    return name


def scenario_period(name: str) -> str:
    if name.endswith("_morning"):
        return "morning"
    if name.endswith("_afternoon"):
        return "afternoon"
    return "unknown"


def scenario_label(name: str) -> str:
    return SCENARIOS.get(name, {}).get("label", name)


def scenario_color(name: str) -> str:
    family = scenario_family(name)
    return SCENARIO_FAMILIES.get(family, {}).get("color", "#95a5a6")
