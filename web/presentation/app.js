import { drawCharts, updateKpis } from "./modules/charts.js"
import { buildFrame, getFrameCount, getFrameDurationMs, loadManifest, loadNetwork, resolveMode } from "./modules/data.js"
import { createMapController } from "./modules/map.js"
import { formatClock } from "./modules/utils.js"

const manifest = await loadManifest()

const state = {
  family: "scenario_4A_v1",
  period: "morning",
  concert: false,
  showEmergency: false,
  visualMode: "vehicles",
  frameIndex: 0,
  frameProgress: 0,
  playbackRate: 10,
  isPlaying: false,
  darkMode: localStorage.getItem("theme") === "dark",
}

const ui = {
  familySelect: document.getElementById("familySelect"),
  periodSelect: document.getElementById("periodSelect"),
  visualModeSelect: document.getElementById("visualModeSelect"),
  playbackRateSlider: document.getElementById("playbackRateSlider"),
  playbackRateValue: document.getElementById("playbackRateValue"),
  concertToggleRow: document.getElementById("concertToggleRow"),
  concertToggle: document.getElementById("concertToggle"),
  emergencyToggle: document.getElementById("emergencyToggle"),
  playPauseButton: document.getElementById("playPauseButton"),
  timeSlider: document.getElementById("timeSlider"),
  timeLabel: document.getElementById("timeLabel"),
  scenarioNote: document.getElementById("scenarioNote"),
  kpiFromSnaroya: document.getElementById("kpiFromSnaroya"),
  kpiToSnaroya: document.getElementById("kpiToSnaroya"),
  kpiQueue: document.getElementById("kpiQueue"),
  kpiEmergency: document.getElementById("kpiEmergency"),
  queueTimelineChart: document.getElementById("queueTimelineChart"),
  queueGrowthChart: document.getElementById("queueGrowthChart"),
  queueChartValue: document.getElementById("queueChartValue"),
  growthChartValue: document.getElementById("growthChartValue"),
  themeToggle: document.getElementById("themeToggle"),
}

const cache = {
  networks: new Map(),
  playbacks: new Map(),
}

let playTimer = null
let lastAnimationTs = null
let currentMode = null

function showAppError(message) {
  if (ui.scenarioNote) {
    ui.scenarioNote.textContent = message
  }
}

const mapController = createMapController({ manifest, ui, darkMode: state.darkMode })

initControls()
initThemeToggle()
mapController.renderAnchors()
mapController.renderEntryPoints()
await renderAll()

function initControls() {
  for (const family of manifest.families) {
    const option = document.createElement("option")
    option.value = family.id
    const desc = family.description
    option.textContent = desc ? `${family.label} - ${desc}` : family.label
    ui.familySelect.appendChild(option)
  }

  ui.familySelect.value = state.family
  ui.periodSelect.value = state.period
  ui.visualModeSelect.value = state.visualMode
  ui.playbackRateSlider.value = String(state.playbackRate)
  ui.playbackRateValue.textContent = `${state.playbackRate}x`
  syncConcertVisibility()

  ui.familySelect.addEventListener("change", async (event) => {
    await selectFamily(event.target.value)
  })

  ui.periodSelect.addEventListener("change", async (event) => {
    state.period = event.target.value
    syncConcertVisibility()
    state.frameIndex = 0
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
    await renderAll()
  })

  ui.emergencyToggle.addEventListener("change", async (event) => {
    state.showEmergency = event.target.checked
    await updateDynamicLayers()
  })

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

  mapController.map.on("zoomend", () => {
    if (state.visualMode === "vehicles") {
      void updateDynamicLayers()
    }
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

function syncConcertVisibility() {
  const visible = state.period === "afternoon"
  ui.concertToggleRow.hidden = !visible
  if (!visible && state.concert) {
    state.concert = false
    ui.concertToggle.checked = false
  }
}

async function selectFamily(familyId) {
  state.family = familyId
  ui.familySelect.value = familyId
  state.frameIndex = 0
  await renderAll()
}

async function renderAll() {
  const networkMeta = manifest.networks[state.family] ?? manifest.networks.scenario_4A_base
  await mapController.ensureNetworkLoaded({
    family: state.family,
    networkMeta,
    loadNetwork: (path) => loadNetwork(path, cache, { onError: showAppError }),
  })

  const mode = await resolveMode({ manifest, state, cache, onError: showAppError })
  currentMode = mode
  mapController.syncVisualMode(mode, state)
  const frameCount = getFrameCount(mode)
  state.frameIndex = Math.min(state.frameIndex, Math.max(frameCount - 1, 0))
  state.frameProgress = 0
  ui.timeSlider.max = String(Math.max(frameCount - 1, 0))
  ui.timeSlider.value = String(state.frameIndex)

  updateScenarioNote(mode)
  updateKpis({ manifest, mode, state, timeS: 0, ui })
  await updateDynamicLayers(mode)
}

async function updateDynamicLayers(existingMode = null) {
  const mode = existingMode ?? currentMode ?? (await resolveMode({ manifest, state, cache, onError: showAppError }))
  currentMode = mode
  const frame = buildFrame({ manifest, state, mode, index: state.frameIndex, progress: state.frameProgress })
  mapController.renderDynamicLayers(frame, state)
  drawCharts({ manifest, mode, state, timeS: frame.time_s, ui })
  ui.timeLabel.textContent = formatClock(frame.time_s, state.period)
  ui.timeSlider.value = String(state.frameIndex)
  updateKpis({ manifest, mode, state, timeS: frame.time_s, ui })
}

function updateScenarioNote(mode) {
  if (mode.kind === "synthetic_midday") {
    ui.scenarioNote.textContent = "Midt pa dagen er et presentasjonsestimat mellom morgen- og ettermiddagsrush."
    return
  }

  if (mode.kind === "real_with_estimate") {
    ui.scenarioNote.textContent = "Konsertvisningen for denne varianten er beregnet fra de kjørte konsertscenarioene."
    return
  }

  if (manifest.scenarios[mode.scenario]?.has_event_overlay) {
    ui.scenarioNote.textContent = "Konsertvisningen bygger pa et eget kjørt scenario."
    return
  }

  ui.scenarioNote.textContent = "Kartet viser simulering av seed 1"
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

  const frameDurationMs = getFrameDurationMs(mode)
  const totalDurationMs = Math.max((frameCount - 1) * frameDurationMs, frameDurationMs)
  let playheadMs = (state.frameIndex + state.frameProgress) * frameDurationMs
  playheadMs = (playheadMs + deltaMs * state.playbackRate) % totalDurationMs

  state.frameIndex = Math.floor(playheadMs / frameDurationMs)
  state.frameProgress = (playheadMs % frameDurationMs) / frameDurationMs
  await updateDynamicLayers(mode)
  playTimer = window.requestAnimationFrame(stepPlayback)
}