import { clamp, round1 } from "./utils.js"

const STORAGE_KEY = "snv-advanced-workbench-v1"

export function loadWorkbenchState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return { version: 1, families: {} }
    }
    const parsed = JSON.parse(raw)
    return {
      version: 1,
      families: parsed.families ?? {},
    }
  } catch {
    return { version: 1, families: {} }
  }
}

export function saveWorkbenchState(workbench) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(workbench))
}

export function familyWorkbench(workbench, familyId) {
  if (!workbench.families[familyId]) {
    workbench.families[familyId] = {
      edge_edits: {},
      artifacts: [],
    }
  }
  return workbench.families[familyId]
}

export function upsertEdgeEdit(workbench, familyId, edgeId, edit) {
  const family = familyWorkbench(workbench, familyId)
  family.edge_edits[edgeId] = {
    ...family.edge_edits[edgeId],
    ...edit,
  }
}

export function removeEdgeEdit(workbench, familyId, edgeId) {
  const family = familyWorkbench(workbench, familyId)
  delete family.edge_edits[edgeId]
}

export function addArtifact(workbench, familyId, artifact) {
  const family = familyWorkbench(workbench, familyId)
  family.artifacts.push({
    id: artifact.id ?? `${artifact.type}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    ...artifact,
  })
}

export function removeArtifact(workbench, familyId, artifactId) {
  const family = familyWorkbench(workbench, familyId)
  family.artifacts = family.artifacts.filter((artifact) => artifact.id !== artifactId)
}

export function clearFamilyWorkbench(workbench, familyId) {
  delete workbench.families[familyId]
}

export function effectiveEdgeProperties(feature, edgeEdit = null) {
  const props = feature?.properties ?? {}
  return {
    id: props.id ?? "",
    name: props.name ?? props.id ?? "",
    lanes: edgeEdit?.lanes ?? props.lanes ?? 0,
    speed_kmh: edgeEdit?.speed_kmh ?? props.speed_kmh ?? 0,
    capacity_vph_estimate: edgeEdit?.capacity_vph_estimate ?? props.capacity_vph_estimate ?? 0,
    length_m: props.length_m ?? 0,
    priority: props.priority ?? 0,
    allowed_classes: props.allowed_classes ?? [],
    signal_id: props.signal_id ?? "",
    roundabout_id: props.roundabout_id ?? "",
    from_node: props.from_node ?? "",
    to_node: props.to_node ?? "",
    from_node_type: props.from_node_type ?? "",
    to_node_type: props.to_node_type ?? "",
    outgoing_edge_ids: props.outgoing_edge_ids ?? [],
    node_edge_ids: props.node_edge_ids ?? [],
    midpoint: props.midpoint ?? [0, 0],
    from_node_coord: props.from_node_coord ?? [0, 0],
    to_node_coord: props.to_node_coord ?? [0, 0],
    lane_details: props.lane_details ?? [],
  }
}

export function computeEdgeLiveMetrics(feature, frame, edgeEdit = null) {
  const edge = effectiveEdgeProperties(feature, edgeEdit)
  const frameEdge = frame?.edges?.[edge.id] ?? [0, edge.speed_kmh, 0, 0]
  const capacityUnits = Math.max(edge.capacity_vph_estimate / 120, edge.lanes * 6, 1)
  const utilizationPct = round1(clamp((frameEdge[0] / capacityUnits) * 100, 0, 999))
  return {
    count: frameEdge[0],
    speed_kmh: frameEdge[1],
    emergency_count: frameEdge[2],
    event_count: frameEdge[3],
    utilization_pct: utilizationPct,
  }
}

export function buildPatchPackage({ familyId, manifest, familyState, edgeLookup }) {
  const edgeEdits = Object.entries(familyState.edge_edits ?? {}).map(([edgeId, edit]) => {
    const feature = edgeLookup(edgeId)
    const props = feature?.properties ?? {}
    return {
      edge_id: edgeId,
      ...edit,
      base: {
        id: edgeId,
        name: props.name ?? edgeId,
        from_node: props.from_node ?? "",
        to_node: props.to_node ?? "",
        lanes: props.lanes ?? 0,
        speed_kmh: props.speed_kmh ?? 0,
        capacity_vph_estimate: props.capacity_vph_estimate ?? 0,
        allowed_classes: props.allowed_classes ?? [],
      },
    }
  })

  const artifacts = (familyState.artifacts ?? []).map((artifact) => {
    const feature = edgeLookup(artifact.edge_id)
    const props = feature?.properties ?? {}
    return {
      ...artifact,
      edge: {
        id: artifact.edge_id,
        name: props.name ?? artifact.edge_id,
        from_node: props.from_node ?? "",
        to_node: props.to_node ?? "",
        lanes: props.lanes ?? 0,
        speed_kmh: props.speed_kmh ?? 0,
        midpoint: props.midpoint ?? [0, 0],
      },
    }
  })

  return {
    version: 1,
    source: "web/presentation/advanced.html",
    created_at: new Date().toISOString(),
    family: familyId,
    family_label: manifest.families.find((family) => family.id === familyId)?.label ?? familyId,
    edge_edits: edgeEdits,
    artifacts,
  }
}

export function downloadPatchPackage(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" })
  const href = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = href
  link.download = filename
  link.click()
  URL.revokeObjectURL(href)
}
