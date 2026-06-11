#!/usr/bin/env python3
"""Shared scenario metadata for simulation, analysis, and reporting."""

from math import isclose
from pathlib import Path


try:
    from scripts.config import PROJECT_ROOT
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution from scripts/
    from config import PROJECT_ROOT
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
        "status": "main",
        "export": True,
        "label": "Base (dagens profil)",
        "ui_description": "dagens 2+3-profil",
        "color": "#2ecc71",
        "description": "Scenario 4A demand on current network",
    },
    "scenario_4A_base_scaled80": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "demand": "4A",
        "demand_scale": 0.8,
        "status": "sensitivity",
        "export": False,
        "label": "Base (dagens profil, 80 % trafikk)",
        "ui_description": "dagens 2+3-profil, 80 % etterspørsel",
        "color": "#58d68d",
        "description": "Scenario 4A demand scaled to 80% on current network",
    },
    "scenario_4A_v1": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "status": "main",
        "export": True,
        "label": "V1",
        "ui_description": "innsnevring Snarøyveien (2+2) + utvidet rundkjøring",
        "color": "#e74c3c",
        "description": "Scenario 4A on official V1 lane layout",
    },
    "scenario_4A_v1_scaled80": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "demand_scale": 0.8,
        "status": "sensitivity",
        "export": False,
        "label": "V1 (80 % trafikk)",
        "ui_description": "innsnevring Snarøyveien (2+2), 80 % etterspørsel",
        "color": "#f1948a",
        "description": "Scenario 4A on official V1 lane layout with demand scaled to 80%",
    },
    "scenario_4A_v2": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v2.net.xml",
        "demand": "4A",
        "status": "main",
        "export": True,
        "label": "V2",
        "ui_description": "V1 + redusert fart",
        "color": "#e67e22",
        "description": "Scenario 4A on official V2 lane layout",
    },
    "scenario_4A_v3": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v3.net.xml",
        "demand": "4A",
        "status": "main",
        "export": True,
        "label": "V3",
        "ui_description": "V1 + signalregulert innkjøring",
        "color": "#8e44ad",
        "description": "Scenario 4A on official V3 lane layout",
    },
    "scenario_1A_base": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "demand": "1A",
        "status": "reference",
        "export": False,
        "label": "Base (Sc. 1A)",
        "color": "#16a085",
        "description": "Scenario 1A demand on current network",
    },
    "scenario_1A_v1": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "1A",
        "status": "reference",
        "export": False,
        "label": "V1 (Sc. 1A)",
        "color": "#c0392b",
        "description": "Scenario 1A demand on official V1 lane layout",
    },
    "scenario_4A_v1_rolfsbukt": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "demand": "4A",
        "status": "exploratory",
        "export": True,
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
        "status": "exploratory",
        "export": True,
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
        "status": "exploratory",
        "export": True,
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
                "status": family.get("status", "unknown"),
                "export": bool(family.get("export", False)),
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


def production_exports(scenarios: dict | None = None) -> list[str]:
    """Return catalog scenarios marked for presentation export."""
    scenario_map = SCENARIOS if scenarios is None else scenarios
    return sorted(name for name, scenario in scenario_map.items() if scenario.get("export"))


def validate_scenario_inputs(scenario_name: str, scenario_def: dict, check_files: bool = True) -> list[str]:
    """Return validation errors for one expanded scenario definition."""
    errors = []
    required = ["family", "period", "demand", "network", "routes", "description", "label", "color", "additional"]
    for key in required:
        if key not in scenario_def:
            errors.append(f"{scenario_name}: missing required key {key}")

    if scenario_def.get("period") not in PERIODS:
        errors.append(f"{scenario_name}: unknown period {scenario_def.get('period')}")

    if check_files:
        network = Path(str(scenario_def.get("network", "")))
        if not network.exists():
            errors.append(f"{scenario_name}: missing network {network}")

        route_files = [Path(item) for item in str(scenario_def.get("routes", "")).split(",") if item]
        if not route_files:
            errors.append(f"{scenario_name}: no route files declared")
        for route_file in route_files:
            if not route_file.exists():
                errors.append(f"{scenario_name}: missing route file {route_file}")

        for additional_file in scenario_def.get("additional", []):
            if not Path(str(additional_file)).exists():
                errors.append(f"{scenario_name}: missing additional file {additional_file}")

    return errors


def find_orphaned_folders(scenarios_dir: Path | None = None, output_dir: Path | None = None, scenarios: dict | None = None) -> dict[str, list[str]]:
    """Find local scenario/output folders not declared in the expanded catalog."""
    scenario_map = SCENARIOS if scenarios is None else scenarios
    scenario_names = set(scenario_map)
    scenario_root = PROJECT_ROOT / "scenarios" if scenarios_dir is None else scenarios_dir
    output_root = PROJECT_ROOT / "output" if output_dir is None else output_dir

    def child_dirs(root: Path) -> list[str]:
        if not root.exists():
            return []
        return sorted(path.name for path in root.iterdir() if path.is_dir() and path.name.startswith("scenario_"))

    return {
        "scenarios": [name for name in child_dirs(scenario_root) if name not in scenario_names],
        "output": [name for name in child_dirs(output_root) if name not in scenario_names],
    }


def validate_scenario_catalog(check_files: bool = True, check_orphans: bool = True) -> dict:
    """Validate the expanded scenario catalog and local scenario folders."""
    errors = []
    warnings = []

    for family_name, family in SCENARIO_FAMILIES.items():
        for key in ["network", "demand", "label", "color", "description", "status"]:
            if key not in family:
                errors.append(f"{family_name}: missing family key {key}")
        if family.get("status") not in {"main", "reference", "sensitivity", "exploratory", "legacy", "local"}:
            warnings.append(f"{family_name}: non-standard status {family.get('status')}")

    for scenario_name, scenario_def in SCENARIOS.items():
        errors.extend(validate_scenario_inputs(scenario_name, scenario_def, check_files=check_files))

    orphans = find_orphaned_folders() if check_orphans else {"scenarios": [], "output": []}
    for root_name, names in orphans.items():
        for name in names:
            warnings.append(f"orphaned {root_name} folder: {name}")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "orphans": orphans,
        "scenario_count": len(SCENARIOS),
        "export_count": len(production_exports()),
    }
