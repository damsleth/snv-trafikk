"""Shared constants and helpers for cross-script consistency.

These values are consumed by both batch analysis and presentation export so
the same scenario data produces the same derived metrics and file locations
everywhere.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"
VISUALIZATIONS_DIR = OUTPUT_DIR / "visualizations"
REPORT_DIR = OUTPUT_DIR / "report"
SUMMARY_STATS_FILE = REPORT_DIR / "summary_stats.json"
PRESENTATION_DIR = PROJECT_ROOT / "web" / "presentation"
PRESENTATION_DATA_DIR = PRESENTATION_DIR / "data"
PRESENTATION_NETWORKS_DIR = PRESENTATION_DATA_DIR / "networks"
PRESENTATION_PLAYBACK_DIR = PRESENTATION_DATA_DIR / "playback"

SIMULATION_BEGIN_S = 0
SIMULATION_END_S = 3600

SNAROYA_ORIGIN_EDGE_IDS = frozenset({"-27195187#3"})
SNAROYA_DESTINATION_EDGE_IDS = frozenset({"27195187#2"})

# Queue density assumption for stopped traffic per lane.
STOPPED_DENSITY_VEH_PER_KM_PER_LANE = 120
SNAROYA_APPROACH_LANES = 2


def lane_edge_id(lane_id: str) -> str:
    """Extract the edge ID from a SUMO lane ID like "edge_0"."""
    return lane_id.rsplit("_", 1)[0] if "_" in lane_id else lane_id


def queue_length_km(vehicle_count: int, lane_count: int = SNAROYA_APPROACH_LANES) -> float:
    """Estimate queue length in kilometers from stopped vehicle count."""
    if lane_count <= 0:
        raise ValueError("lane_count must be positive")
    density = STOPPED_DENSITY_VEH_PER_KM_PER_LANE * lane_count
    return round(vehicle_count / density, 1)
