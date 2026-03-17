import xml.etree.ElementTree as ET

from scripts.utils.patch_generator import build_connection_patches, build_edge_patches, build_metadata


def sample_patch_package() -> dict:
    return {
        "family": "scenario_4A_v1",
        "edge_edits": [
            {
                "edge_id": "edge_a",
                "lanes": 2,
                "speed_kmh": 40,
                "base": {
                    "from_node": "n1",
                    "to_node": "n2",
                    "lanes": 2,
                    "speed_kmh": 50,
                },
            },
        ],
        "artifacts": [
            {
                "id": "artifact-1",
                "type": "cycleway",
                "edge_id": "edge_a",
                "width_m": 2.0,
            },
            {
                "id": "artifact-2",
                "type": "crossing",
                "edge_id": "edge_a",
                "node_id": "n2",
                "crossing_edges": ["edge_a", "edge_b"],
            },
            {
                "id": "artifact-3",
                "type": "median",
                "edge_id": "edge_a",
            },
        ],
    }


def test_build_edge_patches_adds_lane_artifacts() -> None:
    root = build_edge_patches(sample_patch_package())

    edge = root.find("edge")
    assert edge is not None
    assert edge.get("id") == "edge_a"
    assert edge.get("numLanes") == "3"
    lane = edge.find("lane")
    assert lane is not None
    assert lane.get("allow") == "bicycle"


def test_build_connection_patches_emits_crossings() -> None:
    root = build_connection_patches(sample_patch_package())

    crossing = root.find("crossing")
    assert crossing is not None
    assert crossing.get("node") == "n2"
    assert crossing.get("edges") == "edge_a edge_b"


def test_build_metadata_tracks_unsupported_artifacts() -> None:
    metadata = build_metadata(sample_patch_package())

    assert metadata["edge_edit_count"] == 1
    assert metadata["artifact_count"] == 3
    assert len(metadata["unsupported_artifacts"]) == 1
