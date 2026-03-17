#!/usr/bin/env python3
"""Shared scenario metadata for simulation, analysis, and reporting."""

from math import isclose
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


def format_demand_scale(demand_scale: float) -> str:
    """Return a stable string representation for scaled demand file names."""
    if demand_scale <= 0:
        raise ValueError("demand_scale must be positive")
    return f"{demand_scale:.3f}".rstrip("0").rstrip(".")


def demand_scale_suffix(demand_scale: float) -> str:
    if isclose(demand_scale, 1.0, rel_tol=0.0, abs_tol=1e-9):
        return ""
    return f"_scale_{format_demand_scale(demand_scale).replace('.', '_')}"


def demand_route_path(period_name: str, demand: str, demand_scale: float = 1.0) -> Path:
    period = PERIODS[period_name]
    route_name = f"{period['route_suffix']}_{demand}{demand_scale_suffix(demand_scale)}.rou.xml"
    return DEMAND_DIR / "routes" / route_name


def declared_demand_variants(families: dict | None = None) -> list[tuple[str, float]]:
    """Collect unique demand/profile combinations required by declared scenarios."""
    scenario_families = SCENARIO_FAMILIES if families is None else families
    variants = {
        (family["demand"], float(family.get("demand_scale", 1.0)))
        for family in scenario_families.values()
    }
    return sorted(variants, key=lambda item: (item[0], item[1]))

SCENARIO_FAMILIES = {
    "scenario_4A_base": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "demand": "4A",
        "label": "Base (dagens profil)",
        "ui_description": "dagens 2+3-profil",
        "color": "#2ecc71",
        "description": "Scenario 4A demand on current network",
    },
    "scenario_4A_base_scaled80": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "demand": "4A",
        "demand_scale": 0.8,
        "label": "Base (dagens profil, 80 % trafikk)",
        "ui_description": "dagens 2+3-profil, 80 % etterspørsel",
        "color": "#58d68d",
        "description": "Scenario 4A demand scaled to 80% on current network",
    },
    "scenario_4A_v1": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "label": "V1",
        "ui_description": "innsnevring Snarøyveien (2+2) + utvidet rundkjøring",
        "color": "#e74c3c",
        "description": "Scenario 4A on official V1 lane layout",
    },
    "scenario_4A_v1_scaled80": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "demand_scale": 0.8,
        "label": "V1 (80 % trafikk)",
        "ui_description": "innsnevring Snarøyveien (2+2), 80 % etterspørsel",
        "color": "#f1948a",
        "description": "Scenario 4A on official V1 lane layout with demand scaled to 80%",
    },
    "scenario_4A_v2": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v2.net.xml",
        "demand": "4A",
        "label": "V2",
        "ui_description": "V1 + redusert fart",
        "color": "#e67e22",
        "description": "Scenario 4A on official V2 lane layout",
    },
    "scenario_4A_v3": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v3.net.xml",
        "demand": "4A",
        "label": "V3",
        "ui_description": "V1 + signalregulert innkjøring",
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
        "ui_description": "V1 med bilfritt felt langs Rolfsbuktveien",
        "color": "#d35400",
        "description": "V1 lane layout with Rolfsbuktveien miljøgate (15 km/h)",
        "extra_additional": [
            str(NETWORK_DIR / "signals" / "rolfsbukt_miljogate.add.xml"),
        ],
    },
    "scenario_4A_base_event": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "demand": "4A",
        "label": "Base + konsert",
        "color": "#27ae60",
        "description": "Base network with Unity Arena event-night overlay (PM only)",
        "periods": ["afternoon"],
        "extra_routes": [
            str(DEMAND_DIR / "routes" / "event_overlay.rou.xml"),
        ],
    },
    "scenario_4A_v1_event": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "label": "V1 + konsert",
        "color": "#922b21",
        "description": "V1 lane layout with Unity Arena event-night overlay (PM only)",
        "periods": ["afternoon"],
        "extra_routes": [
            str(DEMAND_DIR / "routes" / "event_overlay.rou.xml"),
        ],
    },
}


def build_scenarios(families: dict | None = None) -> dict:
    """Expand families into per-period scenarios."""
    scenarios = {}
    scenario_families = SCENARIO_FAMILIES if families is None else families
    for family_name, family in scenario_families.items():
        allowed_periods = family.get("periods", list(PERIODS.keys()))
        demand_scale = float(family.get("demand_scale", 1.0))
        for period_name, period in PERIODS.items():
            if period_name not in allowed_periods:
                continue
            scenario_name = f"{family_name}_{period_name}"
            additional = [
                str(NETWORK_DIR / "signals" / "roundabout_params.add.xml"),
            ] + family.get("extra_additional", [])
            # Build route file list (base demand + optional overlay)
            routes = str(demand_route_path(period_name, family["demand"], demand_scale))
            extra_routes = family.get("extra_routes", [])
            if extra_routes:
                routes = ",".join([routes] + extra_routes)
            scenarios[scenario_name] = {
                "family": family_name,
                "period": period_name,
                "demand": family["demand"],
                "demand_scale": demand_scale,
                "network": family["network"],
                "routes": routes,
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
