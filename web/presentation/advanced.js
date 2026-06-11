import { drawCharts, updateKpis } from "./modules/charts.js"
import { buildFrame, getFrameCount, getFrameDurationMs, loadManifest, loadNetwork, resolveMode } from "./modules/data.js"
import { computeEdgeLiveMetrics, buildPatchPackage, clearFamilyWorkbench, downloadPatchPackage, effectiveEdgeProperties, familyWorkbench, loadWorkbenchState, removeArtifact, removeEdgeEdit, saveWorkbenchState, upsertEdgeEdit, addArtifact } from "./modules/advanced-tools.js"
import { createMapController } from "./modules/map.js"
import { formatClock } from "./modules/utils.js"

const manifest = await loadManifest()

const ADVANCED_PANEL_WIDTH_STORAGE_KEY = "snv-advanced-panel-width"
const ADVANCED_PANEL_MIN_WIDTH = 450
const ADVANCED_PANEL_MAX_WIDTH = 760

const state = {
  family: "scenario_4A_v1",
  period: "morning",
  concert: false,
  showEmergency: true,
  visualMode: "utilization",
  frameIndex: 0,
  frameProgress: 0,
  playbackRate: 10,
  isPlaying: false,
  darkMode: localStorage.getItem("theme") === "dark",
  showSignals: true,
  showRoundabouts: true,
  showLabels: false,
  selectedEdgeId: null,
  patchedRun: null,
  isRunningPatchedScenario: false,
}

const ui = {
  familySelect: document.getElementById("familySelect"),
  advancedPanel: document.querySelector(".advanced-panel"),
  advancedResizeHandle: document.getElementById("advancedResizeHandle"),
  periodSelect: document.getElementById("periodSelect"),
  visualModeSelect: document.getElementById("visualModeSelect"),
  playbackRateSlider: document.getElementById("playbackRateSlider"),
  playbackRateValue: document.getElementById("playbackRateValue"),
  concertToggleRow: document.getElementById("concertToggleRow"),
  concertToggle: document.getElementById("concertToggle"),
  emergencyToggle: document.getElementById("emergencyToggle"),
  signalsToggle: document.getElementById("signalsToggle"),
  roundaboutsToggle: document.getElementById("roundaboutsToggle"),
  labelsToggle: document.getElementById("labelsToggle"),
  playPauseButton: document.getElementById("playPauseButton"),
  timeSlider: document.getElementById("timeSlider"),
  timeLabel: document.getElementById("timeLabel"),
  themeToggle: document.getElementById("themeToggle"),
  scenarioNote: document.getElementById("scenarioNote"),
  kpiFromSnaroya: document.getElementById("kpiFromSnaroya"),
  kpiToSnaroya: document.getElementById("kpiToSnaroya"),
  kpiQueue: document.getElementById("kpiQueue"),
  kpiEmergency: document.getElementById("kpiEmergency"),
  metricSystemDelay: document.getElementById("metricSystemDelay"),
  metricBlockedVehicles: document.getElementById("metricBlockedVehicles"),
  metricPeakWaiting: document.getElementById("metricPeakWaiting"),
  metricMaxEdgeCount: document.getElementById("metricMaxEdgeCount"),
  selectedEdgePill: document.getElementById("selectedEdgePill"),
  selectedEdgeTitle: document.getElementById("selectedEdgeTitle"),
  selectedEdgeMeta: document.getElementById("selectedEdgeMeta"),
  edgeMetricLoad: document.getElementById("edgeMetricLoad"),
  edgeMetricSpeed: document.getElementById("edgeMetricSpeed"),
  edgeMetricUtilization: document.getElementById("edgeMetricUtilization"),
  edgeMetricSignal: document.getElementById("edgeMetricSignal"),
  editSpeedInput: document.getElementById("editSpeedInput"),
  editLanesInput: document.getElementById("editLanesInput"),
  editCapacityInput: document.getElementById("editCapacityInput"),
  saveEdgeEditButton: document.getElementById("saveEdgeEditButton"),
  resetEdgeEditButton: document.getElementById("resetEdgeEditButton"),
  artifactTypeSelect: document.getElementById("artifactTypeSelect"),
  artifactSideSelect: document.getElementById("artifactSideSelect"),
  artifactWidthInput: document.getElementById("artifactWidthInput"),
  crossingPartnerSelect: document.getElementById("crossingPartnerSelect"),
  addArtifactButton: document.getElementById("addArtifactButton"),
  artifactList: document.getElementById("artifactList"),
  runPatchedScenarioButton: document.getElementById("runPatchedScenarioButton"),
  exportPatchButton: document.getElementById("exportPatchButton"),
  clearWorkbenchButton: document.getElementById("clearWorkbenchButton"),
  queueTimelineChart: document.getElementById("queueTimelineChart"),
  queueGrowthChart: document.getElementById("queueGrowthChart"),
  queueChartValue: document.getElementById("queueChartValue"),
  growthChartValue: document.getElementById("growthChartValue"),
}

const cache = {
  networks: new Map(),
  playbacks: new Map(),
}

const MIN_RENDER_INTERVAL_MS = 33

const workbench = loadWorkbenchState()
let playTimer = null
let lastAnimationTs = null
let lastRenderTs = 0
let lastChartFrameIndex = -1
let currentMode = null
let currentFrame = { time_s: 0, edges: {}, emergency: [], vehicles: [] }

const mapController = createMapController({
  manifest,
  ui,
  darkMode: state.darkMode,
  popupRenderer: renderAdvancedPopup,
  onEdgeSelected: handleEdgeSelected,
})

initControls()
initThemeToggle()
initResizeHandle()
mapController.renderAnchors()
mapController.renderEntryPoints()
await renderAll()

function initControls() {
  for (const family of manifest.families) {
    const option = document.createElement("option")
    option.value = family.id
    option.textContent = family.description ? `${family.label} - ${family.description}` : family.label
    ui.familySelect.appendChild(option)
  }

  ui.familySelect.value = state.family
  ui.periodSelect.value = state.period
  ui.visualModeSelect.value = state.visualMode
  ui.playbackRateSlider.value = String(state.playbackRate)
  ui.playbackRateValue.textContent = `${state.playbackRate}x`
  syncConcertVisibility()

  ui.familySelect.addEventListener("change", async (event) => {
    state.family = event.target.value
    state.frameIndex = 0
    state.selectedEdgeId = null
    invalidatePatchedRun()
    await renderAll()
  })

  ui.periodSelect.addEventListener("change", async (event) => {
    state.period = event.target.value
    state.frameIndex = 0
    invalidatePatchedRun()
    syncConcertVisibility()
    await renderAll()
  })

  ui.visualModeSelect.addEventListener("change", async (event) => {
    state.visualMode = event.target.value
    await updateDynamicLayers()
  })

  ui.playbackRateSlider.addEventListener("input", (event) => {
    state.playbackRate = Number(event.target.value)
    ui.playbackRateValue.textContent = `${state.playbackRate}x`
  })

  ui.concertToggle.addEventListener("change", async (event) => {
    state.concert = event.target.checked
    state.frameIndex = 0
    invalidatePatchedRun()
    await renderAll()
  })

  ui.emergencyToggle.addEventListener("change", async (event) => {
    state.showEmergency = event.target.checked
    await updateDynamicLayers()
  })

  for (const [checkbox, key] of [[ui.signalsToggle, "showSignals"], [ui.roundaboutsToggle, "showRoundabouts"], [ui.labelsToggle, "showLabels"]]) {
    checkbox.addEventListener("change", async (event) => {
      state[key] = event.target.checked
      await updateDynamicLayers()
    })
  }

  ui.playPauseButton.addEventListener("click", () => {
    if (state.isPlaying) {
      stopPlayback()
    } else {
      startPlayback()
    }
  })

  ui.timeSlider.addEventListener("input", async (event) => {
    state.frameIndex = Number(event.target.value)
    state.frameProgress = 0
    await updateDynamicLayers()
  })

  ui.saveEdgeEditButton.addEventListener("click", async () => {
    const feature = selectedFeature()
    if (!feature) {
      showAppError("Velg en lenke før du lagrer en edge-patch.")
      return
    }
    upsertEdgeEdit(workbench, state.family, feature.properties.id, {
      speed_kmh: Number(ui.editSpeedInput.value),
      lanes: Number(ui.editLanesInput.value),
      capacity_vph_estimate: Number(ui.editCapacityInput.value),
    })
    saveWorkbenchState(workbench)
    invalidatePatchedRun("Lokale edge-endringer krever ny kjøring før patched-resultatet oppdateres.")
    await updateDynamicLayers()
    populateEdgeEditor(feature)
    renderArtifactList()
  })

  ui.resetEdgeEditButton.addEventListener("click", async () => {
    const feature = selectedFeature()
    if (!feature) {
      return
    }
    removeEdgeEdit(workbench, state.family, feature.properties.id)
    saveWorkbenchState(workbench)
    invalidatePatchedRun("Patch-resultatet ble ugyldig etter at edge-endringen ble nullstilt.")
    populateEdgeEditor(feature)
    await updateDynamicLayers()
  })

  ui.addArtifactButton.addEventListener("click", async () => {
    const feature = selectedFeature()
    if (!feature) {
      showAppError("Velg en lenke før du legger til et artefakt.")
      return
    }
    const type = ui.artifactTypeSelect.value
    const artifact = {
      type,
      edge_id: feature.properties.id,
      side: ui.artifactSideSelect.value,
      width_m: Number(ui.artifactWidthInput.value),
      node_id: feature.properties.to_node,
    }
    if (type === "crossing") {
      const partner = ui.crossingPartnerSelect.value
      if (!partner) {
        showAppError("Velg en partnerlenke for kryssingen.")
        return
      }
      artifact.crossing_edges = [feature.properties.id, partner]
    }
    addArtifact(workbench, state.family, artifact)
    saveWorkbenchState(workbench)
    invalidatePatchedRun("Artefaktendringer krever ny kjøring før patched-resultatet oppdateres.")
    renderArtifactList()
    await updateDynamicLayers()
  })

  ui.runPatchedScenarioButton.addEventListener("click", async () => {
    await runPatchedScenario()
  })

  ui.exportPatchButton.addEventListener("click", () => {
    const familyState = familyWorkbench(workbench, state.family)
    const payload = buildPatchPackage({
      familyId: state.family,
      manifest,
      familyState,
      edgeLookup: (edgeId) => mapController.getEdgeFeature(edgeId),
    })
    downloadPatchPackage(`${state.family}_advanced_patch.json`, payload)
    showAppError("Patchpakke lastet ned. Kjor patch-generatoren lokalt for XML-filer.")
  })

  ui.clearWorkbenchButton.addEventListener("click", async () => {
    clearFamilyWorkbench(workbench, state.family)
    saveWorkbenchState(workbench)
    invalidatePatchedRun("Lokale endringer er fjernet. Viser igjen basisresultatet for scenarioet.")
    renderArtifactList()
    if (state.selectedEdgeId) {
      populateEdgeEditor(selectedFeature())
    }
    await updateDynamicLayers()
  })

  window.addEventListener("resize", () => {
    void updateDynamicLayers()
  })
}

function initThemeToggle() {
  ui.themeToggle.addEventListener("click", () => {
    state.darkMode = !state.darkMode
    localStorage.setItem("theme", state.darkMode ? "dark" : "light")
    mapController.toggleTheme(state.darkMode)
  })
}

function initResizeHandle() {
  const savedWidth = Number(localStorage.getItem(ADVANCED_PANEL_WIDTH_STORAGE_KEY))
  if (Number.isFinite(savedWidth) && savedWidth > 0) {
    applyAdvancedPanelWidth(savedWidth)
  }

  ui.advancedResizeHandle.addEventListener("pointerdown", (event) => {
    event.preventDefault()
    ui.advancedResizeHandle.setPointerCapture(event.pointerId)
    document.body.classList.add("is-resizing-panel")

    const onPointerMove = (moveEvent) => {
      applyAdvancedPanelWidth(moveEvent.clientX)
    }

    const onPointerUp = (upEvent) => {
      ui.advancedResizeHandle.releasePointerCapture(upEvent.pointerId)
      ui.advancedResizeHandle.removeEventListener("pointermove", onPointerMove)
      ui.advancedResizeHandle.removeEventListener("pointerup", onPointerUp)
      ui.advancedResizeHandle.removeEventListener("pointercancel", onPointerUp)
      document.body.classList.remove("is-resizing-panel")
      void updateDynamicLayers()
    }

    ui.advancedResizeHandle.addEventListener("pointermove", onPointerMove)
    ui.advancedResizeHandle.addEventListener("pointerup", onPointerUp)
    ui.advancedResizeHandle.addEventListener("pointercancel", onPointerUp)
  })
}

function applyAdvancedPanelWidth(width) {
  const maxWidth = Math.max(ADVANCED_PANEL_MIN_WIDTH, Math.min(ADVANCED_PANEL_MAX_WIDTH, window.innerWidth * 0.72))
  const clampedWidth = Math.round(Math.min(Math.max(width, ADVANCED_PANEL_MIN_WIDTH), maxWidth))
  ui.advancedPanel.style.width = `${clampedWidth}px`
  localStorage.setItem(ADVANCED_PANEL_WIDTH_STORAGE_KEY, String(clampedWidth))
}

function selectedFeature() {
  return state.selectedEdgeId ? mapController.getEdgeFeature(state.selectedEdgeId) : null
}

function edgeEditFor(edgeId) {
  return familyWorkbench(workbench, state.family).edge_edits?.[edgeId] ?? null
}

function artifactsForFamily() {
  return familyWorkbench(workbench, state.family).artifacts ?? []
}

function syncConcertVisibility() {
  const visible = state.period === "afternoon"
  ui.concertToggleRow.hidden = !visible
  if (!visible && state.concert) {
    state.concert = false
    ui.concertToggle.checked = false
  }
}

function invalidatePatchedRun(message = null) {
  state.patchedRun = null
  if (currentMode?.patchedRun) {
    currentMode = null
  }
  if (message) {
    ui.scenarioNote.textContent = message
  }
}

function showAppError(message) {
  ui.scenarioNote.textContent = message
}

function setPatchedRunBusy(isBusy) {
  state.isRunningPatchedScenario = isBusy
  ui.runPatchedScenarioButton.disabled = isBusy
  ui.runPatchedScenarioButton.textContent = isBusy ? "Kjører..." : "Kjør patched scenario"
}

async function runPatchedScenario() {
  if (state.period === "midday") {
    showAppError("Patched reruns kan bare kjøres for morgen- eller ettermiddagsrush.")
    return
  }

  const familyState = familyWorkbench(workbench, state.family)
  const payload = buildPatchPackage({
    familyId: state.family,
    manifest,
    familyState,
    edgeLookup: (edgeId) => mapController.getEdgeFeature(edgeId),
  })

  if (!payload.edge_edits.length && !payload.artifacts.length) {
    showAppError("Legg inn minst en edge-endring eller et artefakt før du kjører patched scenario.")
    return
  }

  setPatchedRunBusy(true)
  ui.scenarioNote.textContent = "Starter patched SUMO-kjøring lokalt..."

  try {
    const response = await fetch("/api/patched-run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        family: state.family,
        period: state.period,
        concert: state.concert,
        seed: 1,
        package: payload,
      }),
    })
    const body = await response.json()
    if (!response.ok) {
      throw new Error(body.error || "Klarte ikke å kjøre patched scenario.")
    }

    state.patchedRun = body
    state.frameIndex = 0
    state.frameProgress = 0
    ui.scenarioNote.textContent = body.warnings?.length
      ? body.warnings.join(" ")
      : `Patched scenario ferdig: ${body.scenario}`
    await renderAll()
  } catch (error) {
    showAppError(error.message || "Patched scenario feilet.")
  } finally {
    setPatchedRunBusy(false)
  }
}

function renderAdvancedPopup(feature) {
  const props = feature.properties
  return [
    `<strong>${props.name}</strong>`,
    `ID: ${props.id}`,
    `Felter: ${props.lanes}`,
    `Skiltet fart: ${props.speed_kmh} km/t`,
    `Lengde: ${props.length_m} m`,
    `Kapasitetsanslag: ${props.capacity_vph_estimate} kjt/t`,
    `Koblinger videre: ${props.outgoing_edge_ids.length}`,
    props.signal_id ? `Signal: ${props.signal_id}` : "Signal: nei",
  ].join("<br/>")
}

async function handleEdgeSelected(edgeId) {
  state.selectedEdgeId = edgeId
  const feature = selectedFeature()
  populateEdgeEditor(feature)
  renderArtifactList()
  await updateDynamicLayers()
}

function populateEdgeEditor(feature) {
  if (!feature) {
    ui.selectedEdgePill.textContent = "Ingen valgt"
    ui.selectedEdgeTitle.textContent = "Klikk på en lenke i kartet"
    ui.selectedEdgeMeta.innerHTML = ""
    ui.editSpeedInput.value = ""
    ui.editLanesInput.value = ""
    ui.editCapacityInput.value = ""
    ui.crossingPartnerSelect.innerHTML = ""
    return
  }

  const edgeEdit = edgeEditFor(feature.properties.id)
  const edge = effectiveEdgeProperties(feature, edgeEdit)
  ui.selectedEdgePill.textContent = edgeEdit ? "Lokal patch" : "Original"
  ui.selectedEdgeTitle.textContent = edge.name
  ui.editSpeedInput.value = String(edge.speed_kmh)
  ui.editLanesInput.value = String(edge.lanes)
  ui.editCapacityInput.value = String(edge.capacity_vph_estimate)
  ui.selectedEdgeMeta.innerHTML = buildInspectorRows([
    ["Lenke-ID", edge.id],
    ["Fra node", `${edge.from_node} (${edge.from_node_type || "ukjent"})`],
    ["Til node", `${edge.to_node} (${edge.to_node_type || "ukjent"})`],
    ["Tillatte klasser", edge.allowed_classes.join(", ") || "-"],
    ["Utgående lenker", edge.outgoing_edge_ids.join(", ") || "-"],
    ["Rundkjøring", edge.roundabout_id || "-"],
  ])

  ui.crossingPartnerSelect.innerHTML = ""
  for (const edgeId of edge.node_edge_ids) {
    const option = document.createElement("option")
    option.value = edgeId
    option.textContent = edgeId
    ui.crossingPartnerSelect.appendChild(option)
  }
}

function buildInspectorRows(rows) {
  return rows.map(([term, value]) => `<dt>${term}</dt><dd>${value}</dd>`).join("")
}

async function renderAll() {
  lastChartFrameIndex = -1
  const networkMeta = manifest.networks[state.family] ?? manifest.networks.scenario_4A_base
  await mapController.ensureNetworkLoaded({
    family: state.family,
    networkMeta,
    loadNetwork: (path) => loadNetwork(path, cache, { onError: showAppError }),
  })

  currentMode = state.patchedRun
    ? {
        kind: "real",
        scenario: state.patchedRun.scenario,
        playback: state.patchedRun.playback,
        patchedRun: state.patchedRun,
      }
    : await resolveMode({ manifest, state, cache, onError: showAppError })
  mapController.syncVisualMode(currentMode, state)
  const frameCount = getFrameCount(currentMode)
  state.frameIndex = Math.min(state.frameIndex, Math.max(frameCount - 1, 0))
  state.frameProgress = 0
  ui.timeSlider.max = String(Math.max(frameCount - 1, 0))
  ui.timeSlider.value = String(state.frameIndex)

  updateScenarioSummary(currentMode)
  await updateDynamicLayers(currentMode)
}

function updateScenarioSummary(mode) {
  if (mode.kind === "synthetic_midday") {
    ui.metricSystemDelay.textContent = "syntetisk"
    ui.metricBlockedVehicles.textContent = "syntetisk"
    ui.metricPeakWaiting.textContent = "syntetisk"
    ui.metricMaxEdgeCount.textContent = "-"
    ui.scenarioNote.textContent = "Avansert midtpadag-visning er beregnet mellom morgen- og ettermiddagsrush."
    return
  }

  if (mode.patchedRun) {
    const kpis = mode.patchedRun.kpis ?? {}
    ui.metricSystemDelay.textContent = `${(kpis.system_delay_h ?? 0).toFixed(1)} t`
    ui.metricBlockedVehicles.textContent = `${Math.round(kpis.blocked_vehicles ?? 0)} kjt`
    ui.metricPeakWaiting.textContent = `${Math.round(kpis.peak_waiting ?? 0)} kjt`
    ui.metricMaxEdgeCount.textContent = `${mode.playback?.max_edge_count ?? 0} kjt`
    ui.scenarioNote.textContent = mode.patchedRun.warnings?.length
      ? mode.patchedRun.warnings.join(" ")
      : `Patched kjøring for ${mode.patchedRun.scenario} (seed ${mode.patchedRun.seed}).`
    return
  }

  const scenario = manifest.scenarios[mode.scenario] ?? {}
  const kpis = scenario.kpis ?? {}
  ui.metricSystemDelay.textContent = `${(kpis.system_delay_h ?? 0).toFixed(1)} t`
  ui.metricBlockedVehicles.textContent = `${Math.round(kpis.blocked_vehicles ?? 0)} kjt`
  ui.metricPeakWaiting.textContent = `${Math.round(kpis.peak_waiting ?? 0)} kjt`
  ui.metricMaxEdgeCount.textContent = `${mode.playback?.max_edge_count ?? 0} kjt`
  ui.scenarioNote.textContent = scenario.has_event_overlay
    ? "Konsertvisningen bygger på et eget kjørt scenario."
    : "Avansert visning viser seed 1 med nettverksmetadata og lokale patcher."
}

async function updateDynamicLayers(existingMode = null) {
  const mode = existingMode ?? currentMode ?? (await resolveMode({ manifest, state, cache, onError: showAppError }))
  currentMode = mode
  currentFrame = buildFrame({ manifest, state, mode, index: state.frameIndex, progress: state.frameProgress })
  mapController.renderDynamicLayers(currentFrame, state)
  mapController.renderAdvancedOverlays({
    showLabels: state.showLabels,
    showSignals: state.showSignals,
    showRoundabouts: state.showRoundabouts,
    edgeEdits: familyWorkbench(workbench, state.family).edge_edits,
    artifacts: artifactsForFamily(),
    selectedEdgeId: state.selectedEdgeId,
  })
  ui.timeLabel.textContent = formatClock(currentFrame.time_s, state.period)
  ui.timeSlider.value = String(state.frameIndex)
  updateSelectedEdgeMetrics()
  if (state.frameIndex !== lastChartFrameIndex) {
    lastChartFrameIndex = state.frameIndex
    drawCharts({ manifest, mode, state, timeS: currentFrame.time_s, ui })
    updateKpis({ manifest, mode, state, timeS: currentFrame.time_s, ui })
  }
}

function updateSelectedEdgeMetrics() {
  const feature = selectedFeature()
  if (!feature) {
    ui.edgeMetricLoad.textContent = "-"
    ui.edgeMetricSpeed.textContent = "-"
    ui.edgeMetricUtilization.textContent = "-"
    ui.edgeMetricSignal.textContent = "-"
    return
  }

  const metrics = computeEdgeLiveMetrics(feature, currentFrame, edgeEditFor(feature.properties.id))
  ui.edgeMetricLoad.textContent = `${metrics.count} kjt`
  ui.edgeMetricSpeed.textContent = `${metrics.speed_kmh.toFixed(1)} km/t`
  ui.edgeMetricUtilization.textContent = `${metrics.utilization_pct.toFixed(1)} %`
  ui.edgeMetricSignal.textContent = feature.properties.signal_id || "ingen"
}

function renderArtifactList() {
  const selectedId = state.selectedEdgeId
  const items = artifactsForFamily().filter((artifact) => !selectedId || artifact.edge_id === selectedId)
  if (!items.length) {
    ui.artifactList.innerHTML = '<p class="advanced-note">Ingen artefakter for valgt lenke.</p>'
    return
  }

  ui.artifactList.innerHTML = ""
  for (const artifact of items) {
    const row = document.createElement("div")
    row.className = "artifact-item"
    row.innerHTML = `
      <div>
        <strong>${artifact.type}</strong>
        <p>${artifact.edge_id}${artifact.crossing_edges ? ` - ${artifact.crossing_edges.join(" / ")}` : ""}</p>
      </div>
      <button class="ghost-button" type="button">Fjern</button>
    `
    row.querySelector("button")?.addEventListener("click", async () => {
      removeArtifact(workbench, state.family, artifact.id)
      saveWorkbenchState(workbench)
      renderArtifactList()
      await updateDynamicLayers()
    })
    ui.artifactList.appendChild(row)
  }
}

function startPlayback() {
  if (state.isPlaying) {
    return
  }
  state.isPlaying = true
  ui.playPauseButton.textContent = "Pause"
  lastAnimationTs = null
  playTimer = window.requestAnimationFrame(stepPlayback)
}

function stopPlayback() {
  state.isPlaying = false
  ui.playPauseButton.textContent = "Spill av"
  if (playTimer) {
    window.cancelAnimationFrame(playTimer)
    playTimer = null
  }
  lastAnimationTs = null
}

async function stepPlayback(timestamp) {
  if (!state.isPlaying) {
    return
  }
  const mode = currentMode ?? (await resolveMode({ manifest, state, cache, onError: showAppError }))
  currentMode = mode
  const frameCount = getFrameCount(mode)
  if (frameCount < 2) {
    stopPlayback()
    return
  }

  if (lastAnimationTs == null) {
    lastAnimationTs = timestamp
  }

  const deltaMs = timestamp - lastAnimationTs
  lastAnimationTs = timestamp
  const frameDurationMs = getFrameDurationMs(mode) / state.playbackRate
  const totalProgress = state.frameProgress + deltaMs / Math.max(frameDurationMs, 1)
  const completedFrames = Math.floor(totalProgress)
  state.frameProgress = totalProgress - completedFrames
  state.frameIndex = (state.frameIndex + completedFrames) % frameCount

  if (timestamp - lastRenderTs >= MIN_RENDER_INTERVAL_MS) {
    lastRenderTs = timestamp
    await updateDynamicLayers(mode)
  }
  playTimer = window.requestAnimationFrame(stepPlayback)
}
