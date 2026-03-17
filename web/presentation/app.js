const manifest = await loadManifest();

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
};

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
  compareBody: document.getElementById("compareBody"),
};

const cache = {
  networks: new Map(),
  playbacks: new Map(),
};

const map = L.map("map", {
  zoomControl: true,
  minZoom: 12,
});

const TILES = {
  light: {
    url: "https://cache.kartverket.no/v1/wmts/1.0.0/topograatone/default/webmercator/{z}/{y}/{x}.png",
    attribution: "&copy; Kartverket",
  },
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
};

const activeTile = TILES[state.darkMode ? "dark" : "light"];
let tileLayer = L.tileLayer(activeTile.url, {
  attribution: activeTile.attribution,
  maxZoom: 19,
  subdomains: "abcd",
}).addTo(map);

applyTheme(state.darkMode);

map.fitBounds(manifest.default_bounds);

map.on("moveend zoomend", () => {
  if (localStorage.getItem("debug") === "true") {
    const c = map.getCenter();
    const b = map.getBounds();
    console.debug("[map] center:", [c.lat, c.lng], "zoom:", map.getZoom());
    console.debug("[map] bounds:", [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]]);
  }
});

let networkLayer = null;
let edgeLayers = new Map();
let activeEdges = new Set();
const anchorLayer = L.layerGroup().addTo(map);
const entryPointLayer = L.layerGroup().addTo(map);
const emergencyLayer = L.layerGroup().addTo(map);
const vehicleLayer = L.layerGroup().addTo(map);

let playTimer = null;
let lastAnimationTs = null;
let currentMode = null;

initControls();
initThemeToggle();
renderAnchors();
renderEntryPoints();
await renderAll();
renderComparisonTable();

function initControls() {
  for (const family of manifest.families) {
    const option = document.createElement("option");
    option.value = family.id;
    const desc = family.description;
    option.textContent = desc ? `${family.label} – ${desc}` : family.label;
    ui.familySelect.appendChild(option);
  }
  ui.familySelect.value = state.family;
  ui.periodSelect.value = state.period;
  ui.visualModeSelect.value = state.visualMode;
  ui.playbackRateSlider.value = String(state.playbackRate);
  ui.playbackRateValue.textContent = `${state.playbackRate}x`;
  syncConcertVisibility();

  ui.familySelect.addEventListener("change", async (event) => {
    state.family = event.target.value;
    state.frameIndex = 0;
    await renderAll();
    renderComparisonTable();
  });

  ui.periodSelect.addEventListener("change", async (event) => {
    state.period = event.target.value;
    syncConcertVisibility();
    state.frameIndex = 0;
    await renderAll();
    renderComparisonTable();
  });

  ui.visualModeSelect.addEventListener("change", async (event) => {
    state.visualMode = event.target.value;
    await updateDynamicLayers();
  });

  ui.playbackRateSlider.addEventListener("input", (event) => {
    state.playbackRate = Number(event.target.value);
    ui.playbackRateValue.textContent = `${state.playbackRate}x`;
  });

  ui.concertToggle.addEventListener("change", async (event) => {
    state.concert = event.target.checked;
    state.frameIndex = 0;
    await renderAll();
  });

  ui.emergencyToggle.addEventListener("change", async (event) => {
    state.showEmergency = event.target.checked;
    await updateDynamicLayers();
  });

  ui.playPauseButton.addEventListener("click", () => {
    if (state.isPlaying) {
      stopPlayback();
    } else {
      startPlayback();
    }
  });

  ui.timeSlider.addEventListener("input", async (event) => {
    state.frameIndex = Number(event.target.value);
    state.frameProgress = 0;
    await updateDynamicLayers();
  });

  map.on("zoomend", () => {
    if (state.visualMode === "vehicles") {
      void updateDynamicLayers();
    }
  });

  window.addEventListener("resize", () => {
    void updateDynamicLayers();
  });
}

function syncConcertVisibility() {
  const visible = state.period === "afternoon";
  ui.concertToggleRow.hidden = !visible;
  if (!visible && state.concert) {
    state.concert = false;
    ui.concertToggle.checked = false;
  }
}

function applyTheme(dark) {
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  ui.themeToggle.textContent = dark ? "🌙" : "☀️";
}

function initThemeToggle() {
  ui.themeToggle.addEventListener("click", () => {
    state.darkMode = !state.darkMode;
    localStorage.setItem("theme", state.darkMode ? "dark" : "light");
    applyTheme(state.darkMode);
    /* Swap tile layer (new layer needed for different attribution) */
    const tile = TILES[state.darkMode ? "dark" : "light"];
    map.removeLayer(tileLayer);
    tileLayer = L.tileLayer(tile.url, {
      attribution: tile.attribution,
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(map);
  });
}

function renderComparisonTable() {
  const period = state.period === "midday" ? "morning" : state.period;
  const rows = manifest.families.map((family) => {
    const scenarioKey = `${family.id}_${period}`;
    const kpis = manifest.scenarios[scenarioKey]?.kpis ?? {};
    return {
      id: family.id,
      label: family.label,
      travel_time: kpis.snaroya_avg_min ?? null,
      queue_km: kpis.queue_km ?? null,
      system_delay: kpis.system_delay_h ?? null,
      emergency: kpis.emergency_avg_min ?? null,
    };
  });

  /* Find best/worst for highlighting */
  const metrics = ["travel_time", "queue_km", "system_delay", "emergency"];
  const best = {};
  const worst = {};
  for (const m of metrics) {
    const values = rows.map((r) => r[m]).filter((v) => v != null);
    if (values.length > 0) {
      best[m] = Math.min(...values);
      worst[m] = Math.max(...values);
    }
  }

  const units = {
    travel_time: " min",
    queue_km: " km",
    system_delay: " t",
    emergency: " min",
  };

  ui.compareBody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    if (row.id === state.family) {
      tr.classList.add("compare-active");
    }

    const tdLabel = document.createElement("td");
    tdLabel.textContent = row.label;
    tr.appendChild(tdLabel);

    for (const m of metrics) {
      const td = document.createElement("td");
      if (row[m] != null) {
        const decimals = m === "system_delay" ? 0 : 1;
        td.textContent = `${row[m].toFixed(decimals)}${units[m]}`;
        if (best[m] != null && worst[m] != null && best[m] !== worst[m]) {
          if (row[m] === best[m]) td.classList.add("compare-best");
          else if (row[m] === worst[m]) td.classList.add("compare-worst");
        }
      } else {
        td.textContent = "–";
      }
      tr.appendChild(td);
    }

    tr.style.cursor = "pointer";
    tr.addEventListener("click", () => {
      state.family = row.id;
      ui.familySelect.value = row.id;
      state.frameIndex = 0;
      renderAll();
      renderComparisonTable();
    });

    ui.compareBody.appendChild(tr);
  }
}

async function renderAll() {
  const networkMeta = manifest.networks[state.family] ?? manifest.networks.scenario_4A_base;
  await ensureNetworkLoaded(state.family, networkMeta);

  const mode = await resolveMode();
  currentMode = mode;
  syncVisualMode(mode);
  const frameCount = getFrameCount(mode);
  state.frameIndex = Math.min(state.frameIndex, Math.max(frameCount - 1, 0));
  state.frameProgress = 0;
  ui.timeSlider.max = String(Math.max(frameCount - 1, 0));
  ui.timeSlider.value = String(state.frameIndex);

  updateScenarioNote(mode);
  updateKpis(mode, 0);
  await updateDynamicLayers(mode);
}

function syncVisualMode(mode) {
  const vehicleCapable = mode.kind === "real" && hasVehiclePlayback(mode.playback);
  ui.visualModeSelect.querySelector('option[value="vehicles"]').disabled = !vehicleCapable;
  if (!vehicleCapable && state.visualMode === "vehicles") {
    state.visualMode = "edges";
    ui.visualModeSelect.value = "edges";
  }
}

function hasVehiclePlayback(playback) {
  return Boolean(
    playback?.frames?.some((frame) => Array.isArray(frame.vehicles) && frame.vehicles.length > 0),
  );
}

async function resolveMode() {
  if (state.period === "midday") {
    const morning = await loadPlayback(`${state.family}_morning`);
    const afternoon = await loadPlayback(`${state.family}_afternoon`);
    return {
      kind: "synthetic_midday",
      family: state.family,
      morning,
      afternoon,
    };
  }

  if (state.concert && state.period === "afternoon") {
    const eventScenario = `${state.family}_event_afternoon`;
    const baseScenario = `${state.family}_afternoon`;
    if (manifest.scenarios[eventScenario]) {
      return {
        kind: "real",
        scenario: eventScenario,
        playback: await loadPlayback(eventScenario),
      };
    }
    return {
      kind: "real_with_estimate",
      scenario: baseScenario,
      playback: await loadPlayback(baseScenario),
    };
  }

  const scenario = `${state.family}_${state.period}`;
  return {
    kind: "real",
    scenario,
    playback: await loadPlayback(scenario),
  };
}

function getFrameCount(mode) {
  if (mode.kind === "synthetic_midday") {
    return Math.min(mode.morning.frames.length, mode.afternoon.frames.length);
  }
  return mode.playback?.frames?.length ?? 0;
}

function updateScenarioNote(mode) {
  if (mode.kind === "synthetic_midday") {
    ui.scenarioNote.textContent =
      "Midt pa dagen er et presentasjonsestimat mellom morgen- og ettermiddagsrush.";
    return;
  }

  if (mode.kind === "real_with_estimate") {
    ui.scenarioNote.textContent =
      "Konsertvisningen for denne varianten er beregnet fra de kjørte konsertscenarioene.";
    return;
  }

  if (manifest.scenarios[mode.scenario]?.has_event_overlay) {
    ui.scenarioNote.textContent =
      "Konsertvisningen bygger pa et eget kjørt scenario.";
    return;
  }

  ui.scenarioNote.textContent =
    "Kartet viser simulering av seed 1";
}

function updateKpis(mode, timeS) {
  const kpis = rollingKpiAtTime(mode, timeS);
  ui.kpiFromSnaroya.textContent = kpis.snaroya_from != null ? `${kpis.snaroya_from.toFixed(1)} min` : "–";
  ui.kpiToSnaroya.textContent = kpis.snaroya_to != null ? `${kpis.snaroya_to.toFixed(1)} min` : "–";
  ui.kpiEmergency.textContent = kpis.emergency != null ? `${kpis.emergency.toFixed(1)} min` : "–";
  ui.kpiQueue.textContent = `${kpis.queue_km.toFixed(1)} km`;
}

function rollingKpiAtTime(mode, timeS) {
  const rolling = mode.playback?.rolling_kpis;
  if (!rolling || rolling.length === 0) {
    /* Fallback to static KPIs from manifest */
    const kpis = manifest.scenarios[mode.scenario]?.kpis ?? {};
    return {
      snaroya_from: kpis.snaroya_avg_min ?? null,
      snaroya_to: kpis.snaroya_avg_min ?? null,
      emergency: kpis.emergency_avg_min ?? null,
      queue_km: kpis.queue_km ?? 0,
    };
  }
  /* Binary search for nearest entry */
  let lo = 0, hi = rolling.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (rolling[mid].t <= timeS) lo = mid; else hi = mid - 1;
  }
  const entry = rolling[lo];
  return {
    snaroya_from: entry.snaroya_from ?? null,
    snaroya_to: entry.snaroya_to ?? null,
    emergency: entry.emergency ?? null,
    queue_km: entry.queue_km ?? 0,
  };
}

async function updateDynamicLayers(existingMode = null) {
  const mode = existingMode ?? currentMode ?? (await resolveMode());
  currentMode = mode;
  const frame = buildFrame(mode, state.frameIndex, state.frameProgress);
  drawFrame(frame);
  drawVehicles(frame);
  drawEmergency(frame);
  drawCharts(mode, frame.time_s);
  ui.timeLabel.textContent = formatClock(frame.time_s, state.period);
  ui.timeSlider.value = String(state.frameIndex);
  updateKpis(mode, frame.time_s);
}

function buildFrame(mode, index, progress = 0) {
  if (mode.kind === "synthetic_midday") {
    return buildSyntheticMiddayFrame(mode, index);
  }
  const playback = mode.playback ?? { frames: [], interval_s: 5 };
  const frame = playback.frames[index] ?? playback.frames[0] ?? { t: 0, edges: {}, emergency: [], vehicles: [] };
  const nextIndex = Math.min(index + 1, Math.max(playback.frames.length - 1, 0));
  const nextFrame = playback.frames[nextIndex] ?? frame;
  const interpolated = interpolateRealFrame(frame, nextFrame, progress);
  const adjusted = applyConcertStress(interpolated, mode);
  return {
    time_s: lerp(frame.t, nextFrame.t ?? frame.t, progress),
    edges: adjusted.edges,
    emergency: adjusted.emergency,
    vehicles: adjusted.vehicles ?? interpolated.vehicles ?? [],
  };
}

function buildSyntheticMiddayFrame(mode, index) {
  const morningFrame = mode.morning.frames[index] ?? mode.morning.frames[0];
  const afternoonFrame = mode.afternoon.frames[index] ?? mode.afternoon.frames[0];
  const factor = manifest.synthetic.midday_factor.edge_load;
  const edges = {};
  const union = new Set([
    ...Object.keys(morningFrame?.edges ?? {}),
    ...Object.keys(afternoonFrame?.edges ?? {}),
  ]);

  for (const edgeId of union) {
    const a = morningFrame?.edges?.[edgeId] ?? [0, 0, 0, 0];
    const b = afternoonFrame?.edges?.[edgeId] ?? [0, 0, 0, 0];
    const count = Math.round(((a[0] + b[0]) / 2) * factor);
    const speed = round1(((a[1] + b[1]) / 2) * 1.08);
    const emergencyCount = Math.round((a[2] + b[2]) / 2);
    edges[edgeId] = [count, speed, emergencyCount, 0];
  }

  const syntheticFrame = {
    t: morningFrame?.t ?? afternoonFrame?.t ?? 0,
    edges,
    emergency: morningFrame?.emergency ?? [],
    vehicles: [],
  };
  return {
    time_s: syntheticFrame.t,
    edges: syntheticFrame.edges,
    emergency: syntheticFrame.emergency,
    vehicles: syntheticFrame.vehicles,
  };
}

function applyConcertStress(frame, mode) {
  const edges = {};
  const concertMultiplier = getConcertMultiplier(mode);

  for (const [edgeId, values] of Object.entries(frame.edges ?? {})) {
    const totalMultiplier = clamp(concertMultiplier, 0.65, 6);
    const count = Math.max(0, Math.round(values[0] * totalMultiplier));
    const speed = Math.max(2, round1(values[1] / Math.max(totalMultiplier * 0.82, 0.85)));
    edges[edgeId] = [count, speed, values[2], values[3]];
  }

  return {
    edges,
    emergency: frame.emergency ?? [],
    vehicles: frame.vehicles ?? [],
  };
}

function interpolateRealFrame(frame, nextFrame, progress) {
  const ratio = clamp(progress, 0, 1);
  const edges = {};
  const edgeIds = new Set([
    ...Object.keys(frame.edges ?? {}),
    ...Object.keys(nextFrame.edges ?? {}),
  ]);

  for (const edgeId of edgeIds) {
    const a = frame.edges?.[edgeId] ?? [0, 0, 0, 0];
    const b = nextFrame.edges?.[edgeId] ?? a;
    edges[edgeId] = [
      Math.round(lerp(a[0], b[0], ratio)),
      round1(lerp(a[1], b[1], ratio)),
      Math.round(lerp(a[2], b[2], ratio)),
      Math.round(lerp(a[3], b[3], ratio)),
    ];
  }

  const currentVehicles = new Map((frame.vehicles ?? []).map((vehicle) => [vehicle[0], vehicle]));
  const nextVehicles = new Map((nextFrame.vehicles ?? []).map((vehicle) => [vehicle[0], vehicle]));
  const vehicles = [];

  for (const [vehicleId, vehicle] of currentVehicles) {
    const nextVehicle = nextVehicles.get(vehicleId);
    if (!nextVehicle) {
      vehicles.push(vehicle);
      continue;
    }
    vehicles.push([
      vehicleId,
      lerp(vehicle[1], nextVehicle[1], ratio),
      lerp(vehicle[2], nextVehicle[2], ratio),
      lerp(vehicle[3], nextVehicle[3], ratio),
      vehicle[4],
      lerpAngle(vehicle[5], nextVehicle[5], ratio),
    ]);
  }

  return {
    edges,
    emergency: ratio < 0.5 ? frame.emergency ?? [] : nextFrame.emergency ?? [],
    vehicles,
  };
}

function getConcertMultiplier(mode) {
  if (!(state.concert && state.period === "afternoon")) {
    return 1;
  }
  if (mode.kind === "real" && manifest.scenarios[mode.scenario]?.has_event_overlay) {
    return 1;
  }
  const mapping = {
    scenario_4A_base: "base",
    scenario_4A_v1: "v1",
  };
  const key = mapping[state.family];
  if (key) {
    return manifest.synthetic.event_multipliers[key].system_delay;
  }
  return manifest.synthetic.fallback_event_multipliers.system_delay;
}

function drawFrame(frame) {
  if (state.visualMode === "vehicles") {
    resetEdgeStyling();
    return;
  }
  const nextActive = new Set();

  for (const edgeId of activeEdges) {
    if (!frame.edges[edgeId]) {
      const layer = edgeLayers.get(edgeId);
      if (layer) {
        layer.setStyle(baseEdgeStyle(layer.feature.properties.lanes));
      }
    }
  }

  for (const [edgeId, values] of Object.entries(frame.edges)) {
    const layer = edgeLayers.get(edgeId);
    if (!layer) {
      continue;
    }
    nextActive.add(edgeId);
    const lanes = layer.feature.properties.lanes || 1;
    layer.setStyle(edgeStyle(values[0], values[1], lanes, values[2], values[3]));
  }

  activeEdges = nextActive;
}

function resetEdgeStyling() {
  for (const edgeId of activeEdges) {
    const layer = edgeLayers.get(edgeId);
    if (layer) {
      layer.setStyle(baseEdgeStyle(layer.feature.properties.lanes));
    }
  }
  activeEdges = new Set();
}

function drawEmergency(frame) {
  emergencyLayer.clearLayers();
  if (!state.showEmergency) {
    return;
  }

  /* In "edges" mode, show emergency as dot markers from the edge-level data */
  if (state.visualMode !== "vehicles") {
    for (const item of frame.emergency ?? []) {
      const marker = L.marker([item.lat, item.lon], {
        icon: L.divIcon({
          className: "",
          html: '<div class="emergency-marker"></div>',
          iconSize: [16, 16],
          iconAnchor: [8, 8],
        }),
        zIndexOffset: 10000,
      });
      marker.bindTooltip(`Blålys: ${item.speed.toFixed(0)} km/t`);
      marker.addTo(emergencyLayer);
    }
  }
  /* In "vehicles" mode, emergency vehicles are drawn by drawVehicles
     with high zIndexOffset — nothing extra needed here. */
}

function drawVehicles(frame) {
  vehicleLayer.clearLayers();
  if (state.visualMode !== "vehicles") {
    return;
  }
  if (state.frameIndex === 0 && !state.isPlaying) {
    return;
  }

  const allVehicles = frame.vehicles ?? [];

  /* Draw normal vehicles first, then emergency on top */
  const normalVehicles = [];
  const emergencyVehicles = [];
  for (const vehicle of allVehicles) {
    if (vehicle[4] === 1) {
      emergencyVehicles.push(vehicle);
    } else {
      normalVehicles.push(vehicle);
    }
  }

  for (const vehicle of [...normalVehicles, ...emergencyVehicles]) {
    const [, lat, lon, speedKmh, kind, angle = 0] = vehicle;
    if (!state.showEmergency && kind === 1) {
      continue;
    }
    const style = vehicleStyle(speedKmh, kind, map.getZoom());
    const marker = L.marker([lat, lon], {
      icon: L.divIcon({
        className: kind === 1 ? "vehicle-marker vehicle-marker-emergency" : "vehicle-marker",
        html: vehicleSvg(style, angle),
        iconSize: style.iconSize,
        iconAnchor: style.iconAnchor,
      }),
      zIndexOffset: kind === 1 ? 10000 : 0,
    }).addTo(vehicleLayer);
    if (kind === 1) {
      marker.bindTooltip(`Utrykningskjøretøy: ${Math.round(speedKmh)} km/t`, { direction: "top", offset: [0, -12] });
    } else if (speedKmh > 0) {
      marker.bindTooltip(`${Math.round(speedKmh)} km/t`, { direction: "top", offset: [0, -8] });
    }
  }
}

/* Approach vehicles are now generated by SUMO via expanded OD zones
   (e18_vest, e18_ost, ring3_nord) and included in the FCD playback data. */

function vehicleStyle(speedKmh, kind, zoom) {
  const scale = clamp(Math.pow(1.8, zoom - 15), 0.72, 2.2) * 0.75;
  if (kind === 1) {
    return {
      color: "#facc15",
      opacity: 0.98,
      shape: "emergency",
      iconSize: [Math.round(22 * scale), Math.round(36 * scale)],
      iconAnchor: [Math.round(11 * scale), Math.round(18 * scale)],
    };
  }
  if (kind === 2) {
    return {
      color: "#f59e0b",
      opacity: 0.92,
      shape: "event",
      iconSize: [Math.round(16 * scale), Math.round(26 * scale)],
      iconAnchor: [Math.round(8 * scale), Math.round(13 * scale)],
    };
  }
  /* Colour follows the same logic as edge links:
     standing still / slow = red (hue ≈ 5), flowing freely = green (hue ≈ 120).
     This matches the edge severity colouring so vehicles and road segments
     agree visually: congested = red everywhere, free-flow = green everywhere. */
  const hue = clamp(speedKmh * 3, 5, 120);
  const stopped = speedKmh < 8;
  return {
    color: `hsl(${hue} 78% 52%)`,
    opacity: stopped ? 0.92 : 0.84,
    shape: "car",
    iconSize: [Math.round((stopped ? 15 : 13) * scale), Math.round((stopped ? 28 : 24) * scale)],
    iconAnchor: [Math.round((stopped ? 7.5 : 6.5) * scale), Math.round((stopped ? 14 : 12) * scale)],
  };
}

function vehicleSvg(style, angle) {
  const rotation = Number.isFinite(angle) ? angle : 0;
  if (style.shape === "emergency") {
    /* Blink phase from wall-clock time — survives DOM redraws.
       Alternates left/right every 250ms at a constant rate,
       completely independent of simulation playback speed. */
    const phase = Math.floor(Date.now() / 250) % 2 === 0;
    const leftFill = phase ? "#2563eb" : "#1e3a8a";
    const leftOpacity = phase ? 1 : 0.25;
    const rightFill = phase ? "#1e3a8a" : "#2563eb";
    const rightOpacity = phase ? 0.25 : 1;
    /* Glow intensity pulses on a sine wave (period ≈1s) */
    const glowT = (Math.sin(Date.now() / 160) + 1) / 2;
    const glowR = Math.round(8 + glowT * 12);
    const glowA = (0.5 + glowT * 0.4).toFixed(2);
    const glowFilter =
      `drop-shadow(0 0 ${glowR}px rgba(37,99,235,${glowA})) ` +
      `drop-shadow(0 0 ${glowR * 2}px rgba(37,99,235,${(glowA * 0.5).toFixed(2)}))`;
    return (
      `<svg class="vehicle-svg vehicle-svg-emergency" viewBox="0 0 20 36" width="${style.iconSize[0]}" height="${style.iconSize[1]}" ` +
      `style="transform:rotate(${rotation}deg);transform-origin:center center;filter:${glowFilter}">` +
      `<path class="vehicle-body" d="M6 2h8l3 7v18l-3 7H6l-3-7V9z" style="--vehicle-color:${style.color};--vehicle-opacity:${style.opacity}"/>` +
      `<rect class="vehicle-cabin" x="6.5" y="8" width="7" height="11" rx="2"/>` +
      `<rect class="vehicle-lightbar-left" x="5" y="3.5" width="5" height="3" rx="1.2" style="fill:${leftFill};opacity:${leftOpacity}"/>` +
      `<rect class="vehicle-lightbar-right" x="10" y="3.5" width="5" height="3" rx="1.2" style="fill:${rightFill};opacity:${rightOpacity}"/>` +
      `<path class="vehicle-nose" d="M8 2h4v2H8z"/>` +
      `</svg>`
    );
  }
  if (style.shape === "event") {
    return (
      `<svg class="vehicle-svg" viewBox="0 0 20 34" width="${style.iconSize[0]}" height="${style.iconSize[1]}" ` +
      `style="transform:rotate(${rotation}deg);transform-origin:center center">` +
      `<path class="vehicle-body" d="M5 2h10l3 6v18l-3 6H5l-3-6V8z" style="--vehicle-color:${style.color};--vehicle-opacity:${style.opacity}"/>` +
      `<rect class="vehicle-cabin" x="6" y="8" width="8" height="10" rx="2"/>` +
      `<path class="vehicle-nose" d="M8 3h4v2H8z"/>` +
      `</svg>`
    );
  }
  return (
    `<svg class="vehicle-svg" viewBox="0 0 18 32" width="${style.iconSize[0]}" height="${style.iconSize[1]}" ` +
    `style="transform:rotate(${rotation}deg);transform-origin:center center">` +
    `<path class="vehicle-body" d="M5 2h8l3 6v16l-3 6H5l-3-6V8z" style="--vehicle-color:${style.color};--vehicle-opacity:${style.opacity}"/>` +
    `<rect class="vehicle-cabin" x="5.5" y="8" width="7" height="9" rx="2"/>` +
    `<path class="vehicle-nose" d="M7 3h4v2H7z"/>` +
    `</svg>`
  );
}

function renderAnchors() {
  anchorLayer.clearLayers();
  for (const anchor of manifest.anchors ?? []) {
    const marker = L.marker([anchor.lat, anchor.lon], {
      icon: L.divIcon({
        className: "",
        html: '<div class="anchor-icon"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
      interactive: false,
    }).addTo(anchorLayer);
    marker.bindTooltip(
      `<strong>${anchor.title}</strong>${anchor.detail}`,
      {
        permanent: true,
        direction: anchor.id === "south" ? "right" : "left",
        offset: anchor.id === "south" ? [14, 0] : [-14, 0],
        className: "anchor-tooltip",
      },
    );
  }
}

function renderEntryPoints() {
  entryPointLayer.clearLayers();
  for (const ep of manifest.entry_points ?? []) {
    const bearing = ep.bearing ?? 0;
    const arrowSvg =
      `<svg class="entry-arrow-svg" viewBox="0 0 40 40" width="36" height="36" ` +
      `style="transform:rotate(${bearing}deg);transform-origin:center center">` +
      `<path d="M20 4 L28 18 L23 18 L23 34 L17 34 L17 18 L12 18 Z" ` +
      `fill="#0d5c63" fill-opacity="0.85" stroke="#fff" stroke-width="1.5"/>` +
      `</svg>`;
    const marker = L.marker([ep.lat, ep.lon], {
      icon: L.divIcon({
        className: "entry-point-marker",
        html: `<div class="entry-point-icon">${arrowSvg}</div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      }),
      interactive: true,
    }).addTo(entryPointLayer);
    const tooltipDir = { snaroya: "right", e18_west: "left", e18_east: "right", ring3_north: "left" }[ep.id] ?? "right";
    const tooltipOffset = tooltipDir === "right" ? [22, 0] : [-22, 0];
    marker.bindTooltip(
      `<strong>${ep.title}</strong>${ep.detail}`,
      {
        permanent: true,
        direction: tooltipDir,
        offset: tooltipOffset,
        className: "entry-point-tooltip",
      },
    );
  }
}

function drawCharts(mode, timeS) {
  const series = buildSummarySeries(mode);
  const current = nearestSeriesPoint(series, timeS);
  ui.queueChartValue.textContent = current ? `${Math.round(current.queue)} kjt` : "0 kjt";
  ui.growthChartValue.textContent = current ? `${formatSigned(Math.round(current.growth))} kjt` : "0 kjt";
  drawSeriesChart(ui.queueTimelineChart, series, timeS, {
    stroke: "#fbcd5a",
    fill: "rgba(251, 205, 90, 0.16)",
    valueKey: "queue",
    baseline: 0,
  });
  drawSeriesChart(ui.queueGrowthChart, series, timeS, {
    stroke: "#73d2de",
    fill: "rgba(115, 210, 222, 0.16)",
    valueKey: "growth",
    baseline: 0,
  });
}

function buildSummarySeries(mode) {
  if (mode.kind === "synthetic_midday") {
    const morning = mode.morning?.summary?.queue ?? [];
    const afternoon = mode.afternoon?.summary?.queue ?? [];
    const length = Math.min(morning.length, afternoon.length);
    const series = [];
    for (let index = 0; index < length; index += 1) {
      const a = morning[index];
      const b = afternoon[index];
      const queue = ((a?.[3] ?? 0) + (b?.[3] ?? 0)) / 2 * manifest.synthetic.midday_factor.queue;
      const waiting = ((a?.[1] ?? 0) + (b?.[1] ?? 0)) / 2 * manifest.synthetic.midday_factor.queue;
      const halting = ((a?.[2] ?? 0) + (b?.[2] ?? 0)) / 2 * manifest.synthetic.midday_factor.queue;
      series.push({
        t: a?.[0] ?? b?.[0] ?? 0,
        waiting,
        halting,
        queue,
        growth: 0,
      });
    }
    return withGrowth(series);
  }

  const baseSeries = (mode.playback?.summary?.queue ?? []).map((row) => ({
    t: row[0],
    waiting: row[1],
    halting: row[2],
    queue: row[3],
    growth: row[4],
  }));

  if (state.concert && state.period === "afternoon" && !(mode.kind === "real" && manifest.scenarios[mode.scenario]?.has_event_overlay)) {
    const multiplier = getConcertQueueMultiplier(mode);
    return withGrowth(
      baseSeries.map((point) => ({
        ...point,
        waiting: point.waiting * multiplier,
        halting: point.halting * multiplier,
        queue: point.queue * multiplier,
      })),
    );
  }

  return baseSeries;
}

function getConcertQueueMultiplier(mode) {
  if (!(state.concert && state.period === "afternoon")) {
    return 1;
  }
  if (mode.kind === "real" && manifest.scenarios[mode.scenario]?.has_event_overlay) {
    return 1;
  }
  const mapping = {
    scenario_4A_base: "base",
    scenario_4A_v1: "v1",
  };
  const key = mapping[state.family];
  if (key) {
    return manifest.synthetic.event_multipliers[key].queue;
  }
  return manifest.synthetic.fallback_event_multipliers.queue;
}

function withGrowth(series) {
  let previousQueue = null;
  return series.map((point) => {
    const growth = previousQueue == null ? 0 : point.queue - previousQueue;
    previousQueue = point.queue;
    return { ...point, growth };
  });
}

function nearestSeriesPoint(series, timeS) {
  if (!series.length) {
    return null;
  }
  const interval = Math.max(series[1]?.t - series[0]?.t || 5, 1);
  const index = clamp(Math.round(timeS / interval), 0, series.length - 1);
  return series[index];
}

function drawSeriesChart(canvas, series, timeS, options) {
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }
  const width = canvas.clientWidth || 300;
  const height = canvas.clientHeight || 120;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, width, height);

  const padding = { top: 12, right: 12, bottom: 18, left: 12 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const baseline = options.baseline ?? 0;
  const values = series.length ? series.map((point) => point[options.valueKey]) : [0];
  const minValue = Math.min(...values, baseline);
  const maxValue = Math.max(...values, baseline, 1);
  const valueSpan = Math.max(maxValue - minValue, 1);
  const maxTime = series.at(-1)?.t ?? 0;

  context.strokeStyle = "rgba(255,255,255,0.14)";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(padding.left, padding.top + chartHeight);
  context.lineTo(padding.left + chartWidth, padding.top + chartHeight);
  context.stroke();

  if (!series.length) {
    return;
  }

  const yForValue = (value) => padding.top + chartHeight - ((value - minValue) / valueSpan) * chartHeight;
  const xForTime = (value) => padding.left + (maxTime > 0 ? (value / maxTime) * chartWidth : 0);
  const baselineY = yForValue(baseline);

  context.fillStyle = options.fill;
  context.beginPath();
  context.moveTo(xForTime(series[0].t), baselineY);
  for (const point of series) {
    context.lineTo(xForTime(point.t), yForValue(point[options.valueKey]));
  }
  context.lineTo(xForTime(series.at(-1).t), baselineY);
  context.closePath();
  context.fill();

  context.strokeStyle = options.stroke;
  context.lineWidth = 2;
  context.beginPath();
  for (const [index, point] of series.entries()) {
    const x = xForTime(point.t);
    const y = yForValue(point[options.valueKey]);
    if (index === 0) {
      context.moveTo(x, y);
    } else {
      context.lineTo(x, y);
    }
  }
  context.stroke();

  const playheadX = xForTime(Math.min(Math.max(timeS, 0), maxTime));
  context.strokeStyle = "rgba(255,255,255,0.88)";
  context.lineWidth = 1.25;
  context.beginPath();
  context.moveTo(playheadX, padding.top);
  context.lineTo(playheadX, padding.top + chartHeight);
  context.stroke();
}

function formatSigned(value) {
  if (value > 0) {
    return `+${value}`;
  }
  return String(value);
}

function calculateKpis(mode) {
  if (mode.kind === "synthetic_midday") {
    const morning = manifest.scenarios[`${state.family}_morning`]?.kpis;
    const afternoon = manifest.scenarios[`${state.family}_afternoon`]?.kpis;
    const base = averageKpis(morning, afternoon);
    return applyKpiStress(base, mode, true);
  }

  const base = manifest.scenarios[mode.scenario]?.kpis ?? emptyKpis();
  return applyKpiStress(base, mode, false);
}

function applyKpiStress(base, mode, midday) {
  const result = { ...base };
  if (midday) {
    result.avg_duration_min *= manifest.synthetic.midday_factor.avg_duration;
    result.system_delay_h *= manifest.synthetic.midday_factor.system_delay;
    result.queue_km *= manifest.synthetic.midday_factor.queue;
    result.emergency_avg_min *= manifest.synthetic.midday_factor.emergency;
  }

  if (state.concert && state.period === "afternoon" && !(mode.kind === "real" && manifest.scenarios[mode.scenario]?.has_event_overlay)) {
    const mapping = {
      scenario_4A_base: "base",
      scenario_4A_v1: "v1",
    };
    const key = mapping[state.family];
    const multipliers = key
      ? manifest.synthetic.event_multipliers[key]
      : manifest.synthetic.fallback_event_multipliers;
    result.avg_duration_min *= multipliers.avg_duration;
    result.system_delay_h *= multipliers.system_delay;
    result.queue_km *= multipliers.queue;
    result.emergency_avg_min *= multipliers.emergency;
  }

  return result;
}

function averageKpis(a = emptyKpis(), b = emptyKpis()) {
  return {
    avg_duration_min: (a.avg_duration_min + b.avg_duration_min) / 2,
    system_delay_h: (a.system_delay_h + b.system_delay_h) / 2,
    queue_km: (a.queue_km + b.queue_km) / 2,
    blocked_vehicles: (a.blocked_vehicles + b.blocked_vehicles) / 2,
    peak_waiting: (a.peak_waiting + b.peak_waiting) / 2,
    emergency_avg_min: (a.emergency_avg_min + b.emergency_avg_min) / 2,
    snaroya_avg_min: (a.snaroya_avg_min + b.snaroya_avg_min) / 2,
  };
}

function emptyKpis() {
  return {
    avg_duration_min: 0,
    system_delay_h: 0,
    queue_km: 0,
    blocked_vehicles: 0,
    peak_waiting: 0,
    emergency_avg_min: 0,
    snaroya_avg_min: 0,
  };
}

async function ensureNetworkLoaded(family, networkMeta) {
  if (networkLayer && networkLayer.familyId === family) {
    return;
  }

  if (networkLayer) {
    map.removeLayer(networkLayer);
    edgeLayers = new Map();
    activeEdges = new Set();
  }

  const geojson = await loadNetwork(networkMeta.file);
  networkLayer = L.geoJSON(geojson, {
    style: (feature) => baseEdgeStyle(feature.properties.lanes),
    onEachFeature: (feature, layer) => {
      edgeLayers.set(feature.properties.id, layer);
      layer.bindPopup(
        `<strong>${feature.properties.name}</strong><br/>` +
          `Felter: ${feature.properties.lanes}<br/>` +
          `Skiltet fart: ${feature.properties.speed_kmh} km/t`,
      );
    },
  }).addTo(map);
  networkLayer.familyId = family;
}

function baseEdgeStyle(lanes = 1) {
  return {
    color: "#a8b7b3",
    weight: 1.2 + lanes * 0.45,
    opacity: 0.55,
  };
}

function edgeStyle(count, speedKmh, lanes, emergencyCount, eventCount) {
  const loadPerLane = count / Math.max(lanes, 1);
  const severity = clamp(loadPerLane / 5 + Math.max(0, 28 - speedKmh) / 28, 0, 1.4);
  const hue = clamp(170 - severity * 150, 10, 170);
  const lightness = clamp(48 - severity * 10, 28, 52);
  const saturation = eventCount > 0 ? 82 : 74;
  return {
    color: `hsl(${hue} ${saturation}% ${lightness}%)`,
    weight: 1.4 + Math.min(loadPerLane, 6) * 0.9 + emergencyCount * 0.4,
    opacity: 0.92,
  };
}

function formatClock(timeSeconds, period) {
  const starts = {
    morning: [7, 45],
    midday: [12, 0],
    afternoon: [15, 30],
  };
  const [hour, minute] = starts[period] ?? [12, 0];
  const startSeconds = hour * 3600 + minute * 60;
  const totalSeconds = Math.max(0, Math.floor(startSeconds + timeSeconds));
  const hh = String(Math.floor(totalSeconds / 3600) % 24).padStart(2, "0");
  const mm = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const ss = String(totalSeconds % 60).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function startPlayback() {
  if (state.isPlaying) {
    return;
  }
  state.isPlaying = true;
  ui.playPauseButton.textContent = "Pause";
  lastAnimationTs = null;
  playTimer = window.requestAnimationFrame(stepPlayback);
}

function stopPlayback() {
  state.isPlaying = false;
  ui.playPauseButton.textContent = "Spill av";
  if (playTimer) {
    window.cancelAnimationFrame(playTimer);
    playTimer = null;
  }
  lastAnimationTs = null;
}

async function stepPlayback(timestamp) {
  if (!state.isPlaying) {
    return;
  }
  const mode = currentMode ?? (await resolveMode());
  currentMode = mode;
  const frameCount = getFrameCount(mode);
  if (frameCount < 2) {
    stopPlayback();
    return;
  }

  if (lastAnimationTs == null) {
    lastAnimationTs = timestamp;
  }
  const deltaMs = timestamp - lastAnimationTs;
  lastAnimationTs = timestamp;

  const frameDurationMs = getFrameDurationMs(mode);
  const totalDurationMs = Math.max((frameCount - 1) * frameDurationMs, frameDurationMs);
  let playheadMs = (state.frameIndex + state.frameProgress) * frameDurationMs;
  playheadMs = (playheadMs + deltaMs * state.playbackRate) % totalDurationMs;

  state.frameIndex = Math.floor(playheadMs / frameDurationMs);
  state.frameProgress = (playheadMs % frameDurationMs) / frameDurationMs;
  await updateDynamicLayers(mode);
  playTimer = window.requestAnimationFrame(stepPlayback);
}

function getFrameDurationMs(mode) {
  if (mode.kind === "synthetic_midday") {
    return (mode.morning?.interval_s ?? 5) * 1000;
  }
  return (mode.playback?.interval_s ?? 5) * 1000;
}

async function loadNetwork(path) {
  if (!cache.networks.has(path)) {
    cache.networks.set(path, fetchJson(`./${path}`));
  }
  return cache.networks.get(path);
}

async function loadPlayback(scenarioName) {
  const scenario = manifest.scenarios[scenarioName];
  if (!scenario) {
    return { frames: [], interval_s: 15 };
  }
  const key = scenario.playback.file;
  if (!cache.playbacks.has(key)) {
    cache.playbacks.set(key, fetchJson(`./${key}`));
  }
  return cache.playbacks.get(key);
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function lerpAngle(a, b, t) {
  let delta = ((b - a + 540) % 360) - 180;
  return (a + delta * t + 360) % 360;
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    const error = new Error(`Kunne ikke laste ${path}`);
    showAppError(error.message);
    throw error;
  }
  return response.json();
}

async function loadManifest() {
  try {
    return await fetchJson("./data/manifest.json");
  } catch (error) {
    document.body.innerHTML = `<main class="app-error"><h1>Presentasjonen kunne ikke lastes</h1><p>${error.message}</p></main>`;
    throw error;
  }
}

function showAppError(message) {
  if (ui.scenarioNote) {
    ui.scenarioNote.textContent = message;
  }
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}
