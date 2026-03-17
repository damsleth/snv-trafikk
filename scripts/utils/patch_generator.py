"""Translate advanced presentation patch JSON into SUMO patch files."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def load_patch_package(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_edge_patches(package: dict) -> ET.Element:
    root = ET.Element("edges")
    artifacts_by_edge: dict[str, list[dict]] = {}
    for artifact in package.get("artifacts", []):
        artifacts_by_edge.setdefault(artifact["edge_id"], []).append(artifact)

    for patch in package.get("edge_edits", []):
        base = patch.get("base", {})
        artifacts = artifacts_by_edge.get(patch["edge_id"], [])
        added_sidewalks = sum(1 for artifact in artifacts if artifact.get("type") == "sidewalk")
        added_cycleways = sum(1 for artifact in artifacts if artifact.get("type") == "cycleway")
        num_lanes = int(patch.get("lanes") or base.get("lanes") or 1) + added_sidewalks + added_cycleways
        speed_mps = float(patch.get("speed_kmh") or base.get("speed_kmh") or 0) / 3.6
        edge_el = ET.SubElement(
            root,
            "edge",
            {
                "id": patch["edge_id"],
                "from": base.get("from_node", ""),
                "to": base.get("to_node", ""),
                "speed": f"{speed_mps:.2f}",
                "numLanes": str(num_lanes),
            },
        )

        lane_index = int(patch.get("lanes") or base.get("lanes") or 1)
        for artifact in artifacts:
            if artifact.get("type") == "sidewalk":
                lane_el = ET.SubElement(edge_el, "lane", {"index": str(lane_index), "allow": "pedestrian"})
                if artifact.get("width_m"):
                    lane_el.set("width", f"{float(artifact['width_m']):.1f}")
                lane_index += 1
            if artifact.get("type") == "cycleway":
                lane_el = ET.SubElement(edge_el, "lane", {"index": str(lane_index), "allow": "bicycle"})
                if artifact.get("width_m"):
                    lane_el.set("width", f"{float(artifact['width_m']):.1f}")
                lane_index += 1

    ET.indent(root, space="  ")
    return root


def build_connection_patches(package: dict) -> ET.Element:
    root = ET.Element("connections")
    seen = set()
    for artifact in package.get("artifacts", []):
        if artifact.get("type") != "crossing":
            continue
        edges = artifact.get("crossing_edges") or []
        node_id = artifact.get("node_id") or artifact.get("edge", {}).get("to_node")
        if len(edges) != 2 or not node_id:
            continue
        crossing_key = (node_id, tuple(edges))
        if crossing_key in seen:
            continue
        seen.add(crossing_key)
        ET.SubElement(root, "crossing", {"node": node_id, "edges": " ".join(edges)})

    ET.indent(root, space="  ")
    return root


def build_metadata(package: dict) -> dict:
    supported = {"cycleway", "sidewalk", "crossing"}
    unsupported = [artifact for artifact in package.get("artifacts", []) if artifact.get("type") not in supported]
    return {
        "family": package.get("family"),
        "edge_edit_count": len(package.get("edge_edits", [])),
        "artifact_count": len(package.get("artifacts", [])),
        "unsupported_artifacts": unsupported,
    }


def write_patch_bundle(package: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    edge_tree = ET.ElementTree(build_edge_patches(package))
    edge_tree.write(output_dir / "advanced_patch.edg.xml", encoding="utf-8", xml_declaration=True)

    connection_tree = ET.ElementTree(build_connection_patches(package))
    connection_tree.write(output_dir / "advanced_patch.con.xml", encoding="utf-8", xml_declaration=True)

    (output_dir / "advanced_patch.meta.json").write_text(
        json.dumps(build_metadata(package), indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SUMO patch files from advanced presentation patch JSON")
    parser.add_argument("--input", required=True, type=Path, help="Path to downloaded advanced patch JSON")
    parser.add_argument("--output", required=True, type=Path, help="Directory for generated .edg.xml/.con.xml files")
    args = parser.parse_args()

    package = load_patch_package(args.input)
    write_patch_bundle(package, args.output)
    print(f"Patch bundle -> {args.output}")


if __name__ == "__main__":
    main()
