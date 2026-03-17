import xml.etree.ElementTree as ET

from scripts.utils.patch_generator import build_edge_patches
from scripts.utils.patched_run import apply_artifact_lane_permissions, resolve_target_scenario


def test_build_edge_patches_supports_artifact_only_edges() -> None:
    root = build_edge_patches(
        {
            "artifacts": [
                {
                    "id": "artifact-1",
                    "type": "sidewalk",
                    "edge_id": "edge_a",
                    "width_m": 2.5,
                    "edge": {
                        "from_node": "n1",
                        "to_node": "n2",
                        "lanes": 2,
                        "speed_kmh": 40,
                    },
                },
            ],
        }
    )

    edge = root.find("edge")
    assert edge is not None
    assert edge.get("id") == "edge_a"
    assert edge.get("numLanes") == "3"


def test_apply_artifact_lane_permissions_marks_added_lanes(tmp_path) -> None:
    net_file = tmp_path / "patched.net.xml"
    net_file.write_text(
        """<?xml version='1.0' encoding='utf-8'?>
<net>
  <edge id='edge_a'>
    <lane id='edge_a_0' index='0' speed='10.0' length='10.0'/>
    <lane id='edge_a_1' index='1' speed='10.0' length='10.0'/>
    <lane id='edge_a_2' index='2' speed='10.0' length='10.0'/>
  </edge>
</net>
""",
        encoding="utf-8",
    )

    apply_artifact_lane_permissions(
        net_file,
        {
            "edge_edits": [
                {
                    "edge_id": "edge_a",
                    "lanes": 2,
                    "base": {"lanes": 2},
                }
            ],
            "artifacts": [
                {
                    "type": "sidewalk",
                    "edge_id": "edge_a",
                    "width_m": 2.0,
                }
            ],
        },
    )

    tree = ET.parse(net_file)
    lanes = tree.getroot().find("edge").findall("lane")
    assert lanes[2].get("allow") == "pedestrian"
    assert lanes[2].get("width") == "2.0"


def test_resolve_target_scenario_uses_event_overlay_when_available() -> None:
    assert resolve_target_scenario("scenario_4A_v1", "afternoon", concert=True) == "scenario_4A_v1_event_afternoon"


def test_resolve_target_scenario_rejects_midday() -> None:
    try:
        resolve_target_scenario("scenario_4A_v1", "midday", concert=False)
    except ValueError as exc:
        assert "morning and afternoon" in str(exc)
    else:
        raise AssertionError("Expected resolve_target_scenario to reject midday")