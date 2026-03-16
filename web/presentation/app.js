const manifest = await fetchJson("./data/manifest.json");

const state = {
  family: "scenario_4A_base",
  period: "morning",
  concert: false,
  showEmergency: true,
  busLevel: 100,
  pedestrianLevel: 100,
  pulseLevel: 70,
  frameIndex: 0,
  isPlaying: false,
};

const ui = {
  familySelect: document.getElementById("familySelect"),
  periodSelect: document.getElementById("periodSelect"),
  concertToggle: document.getElementById("concertToggle"),
  emergencyToggle: document.getElementById("emergencyToggle"),
  busSlider: document.getElementById("busSlider"),
  busValue: document.getElementById("busValue"),
  pedestrianSlider: document.getElementById("pedestrianSlider"),
  pedestrianValue: document.getElementById("pedestrianValue"),
  pulseSlider: document.getElementById("pulseSlider"),
  pulseValue: document.getElementById("pulseValue"),
  playPauseButton: document.getElementById("playPauseButton"),
  timeSlider: document.getElementById("timeSlider"),
  timeLabel: document.getElementById("timeLabel"),
  modeBadge: document.getElementById("modeBadge"),
  scenarioNote: document.getElementById("scenarioNote"),
  kpiDuration: document.getElementById("kpiDuration"),
  kpiDelay: document.getElementById("kpiDelay"),
  kpiQueue: document.getElementById("kpiQueue"),
  kpiEmergency: document.getElementById("kpiEmergency"),
};

const cache = {
  networks: new Map(),
  playbacks: new Map(),
};

const map = L.map("map", {
  zoomControl: true,
  minZoom: 12,
});

L.tileLayer(
  "https://cache.kartverket.no/v1/wmts/1.0.0/topograatone/default/webmercator/{z}/{y}/{x}.png",
  {
    attribution: "&copy; Kartverket",
    maxZoom: 19,
  },
).addTo(map);

map.fitBounds(manifest.default_bounds);

let networkLayer = null;
let edgeLayers = new Map();
let activeEdges = new Set();
const emergencyLayer = L.layerGroup().addTo(map);
const busLayer = L.layerGroup().addTo(map);
const pulseLayer = L.layerGroup().addTo(map);

let playTimer = null;

initControls();
await renderAll();

function initControls() {
  for (const family of manifest.families) {
    const option = document.createElement("option");
    option.value = family.id;
    option.textContent = family.label;
    ui.familySelect.appendChild(option);
  }
  ui.familySelect.value = state.family;
  ui.periodSelect.value = state.period;

  ui.familySelect.addEventListener("change", async (event) => {
    state.family = event.target.value;
    state.frameIndex = 0;
    await renderAll();
  });

  ui.periodSelect.addEventListener("change", async (event) => {
    state.period = event.target.value;
    state.frameIndex = 0;
    await renderAll();
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

  bindRange(ui.busSlider, ui.busValue, async (value) => {
    state.busLevel = value;
    await updateDynamicLayers();
  });
  bindRange(ui.pedestrianSlider, ui.pedestrianValue, async (value) => {
    state.pedestrianLevel = value;
    await updateDynamicLayers();
  });
  bindRange(ui.pulseSlider, ui.pulseValue, async (value) => {
    state.pulseLevel = value;
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
    await updateDynamicLayers();
  });
}

function bindRange(slider, output, callback) {
  output.textContent = `${slider.value}%`;
  slider.addEventListener("input", async (event) => {
    const value = Number(event.target.value);
    output.textContent = `${value}%`;
    await callback(value);
  });
}

async function renderAll() {
  const networkMeta = manifest.networks[state.family] ?? manifest.networks.scenario_4A_base;
  await ensureNetworkLoaded(state.family, networkMeta);

  const mode = await resolveMode();
  const frameCount = getFrameCount(mode);
  state.frameIndex = Math.min(state.frameIndex, Math.max(frameCount - 1, 0));
  ui.timeSlider.max = String(Math.max(frameCount - 1, 0));
  ui.timeSlider.value = String(state.frameIndex);

  updateModeBadge(mode);
  updateScenarioNote(mode);
  updateKpis(mode);
  await updateDynamicLayers(mode);
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

function updateModeBadge(mode) {
  if (mode.kind === "synthetic_midday") {
    ui.modeBadge.textContent = "Syntetisk mellomrush";
    return;
  }
  if (mode.kind === "real_with_estimate") {
    ui.modeBadge.textContent = "SUMO + presentasjonsestimat";
    return;
  }
  const isPureReal =
    !state.concert &&
    state.busLevel === 100 &&
    state.pedestrianLevel === 100 &&
    state.pulseLevel === 70;
  ui.modeBadge.textContent = isPureReal ? "Ekte SUMO-kjøring" : "SUMO + presentasjonslag";
}

function updateScenarioNote(mode) {
  if (mode.kind === "synthetic_midday") {
    ui.scenarioNote.textContent =
      "Midt på dagen er interpolert fra morgen- og ettermiddagsrush. Dette er et presentasjonsestimat, ikke en egen SUMO-kjøring.";
    return;
  }

  if (mode.kind === "real_with_estimate") {
    ui.scenarioNote.textContent =
      "Konsertlag for denne varianten estimeres fra kjørte event-scenarioer for base og V1. Kartet viser SUMO-grunnscenario med påslag.";
    return;
  }

  if (manifest.scenarios[mode.scenario]?.has_event_overlay) {
    ui.scenarioNote.textContent =
      "Konsertscenarioet bygger på reell SUMO-kjøring med Unity Arena-event-overlay.";
    return;
  }

  ui.scenarioNote.textContent =
    "Veglenkene viser reell SUMO-avspilling for seed 1. Buss- og fotgjengerlagene er presentasjonskontroller over den kjørte simuleringen.";
}

function updateKpis(mode) {
  const kpis = calculateKpis(mode);
  ui.kpiDuration.textContent = `${kpis.avg_duration_min.toFixed(1)} min`;
  ui.kpiDelay.textContent = `${kpis.system_delay_h.toFixed(0)} kjt-t`;
  ui.kpiQueue.textContent = `${kpis.queue_km.toFixed(1)} km`;
  ui.kpiEmergency.textContent = `${kpis.emergency_avg_min.toFixed(1)} min`;
}

async function updateDynamicLayers(existingMode = null) {
  const mode = existingMode ?? (await resolveMode());
  const frame = buildFrame(mode, state.frameIndex);
  drawFrame(frame);
  drawEmergency(frame);
  drawBuses(frame.time_s);
  drawPedestrianPulses(frame.time_s);
  ui.timeLabel.textContent = formatClock(frame.time_s, state.period);
  ui.timeSlider.value = String(state.frameIndex);
  updateKpis(mode);
}

function buildFrame(mode, index) {
  if (mode.kind === "synthetic_midday") {
    return buildSyntheticMiddayFrame(mode, index);
  }
  const frame = mode.playback.frames[index] ?? mode.playback.frames[0] ?? { t: 0, edges: {}, emergency: [] };
  const adjusted = applySyntheticStress(frame, mode);
  return {
    time_s: frame.t,
    edges: adjusted.edges,
    emergency: adjusted.emergency,
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
  };
  const adjusted = applySyntheticStress(syntheticFrame, mode);
  return {
    time_s: syntheticFrame.t,
    edges: adjusted.edges,
    emergency: adjusted.emergency,
  };
}

function applySyntheticStress(frame, mode) {
  const edges = {};
  const concertMultiplier = getConcertMultiplier(mode);
  const busMultiplier = 1 + ((state.busLevel - 100) / 100) * manifest.synthetic.bus_penalty_per_100pct;
  const pedestrianBase = 1 + ((state.pedestrianLevel - 100) / 100) * manifest.synthetic.pedestrian_penalty_per_100pct;
  const pulseWave = pulseEnvelope(frame.t);
  const pulseMultiplier =
    1 + (state.pulseLevel / 100) * manifest.synthetic.pulse_penalty_max * pulseWave;

  for (const [edgeId, values] of Object.entries(frame.edges ?? {})) {
    const layer = edgeLayers.get(edgeId);
    const name = layer?.feature?.properties?.name ?? "";
    const hotspotMultiplier = isPedestrianHotspot(name) ? pedestrianBase * pulseMultiplier : 1;
    const totalMultiplier = clamp(concertMultiplier * busMultiplier * hotspotMultiplier, 0.65, 6);
    const count = Math.max(0, Math.round(values[0] * totalMultiplier));
    const speed = Math.max(2, round1(values[1] / Math.max(totalMultiplier * 0.82, 0.85)));
    edges[edgeId] = [count, speed, values[2], values[3]];
  }

  return {
    edges,
    emergency: frame.emergency ?? [],
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

function drawEmergency(frame) {
  emergencyLayer.clearLayers();
  if (!state.showEmergency) {
    return;
  }

  for (const item of frame.emergency ?? []) {
    const marker = L.marker([item.lat, item.lon], {
      icon: L.divIcon({
        className: "",
        html: '<div class="emergency-marker"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
    });
    marker.bindTooltip(`Blålys: ${item.speed.toFixed(0)} km/t`);
    marker.addTo(emergencyLayer);
  }
}

function drawBuses(timeSeconds) {
  busLayer.clearLayers();
  const networkMeta = manifest.networks[state.family] ?? manifest.networks.scenario_4A_base;
  const route = networkMeta.bus_route ?? [];
  if (route.length < 2) {
    return;
  }

  const baseBusCount = state.period === "afternoon" ? 5 : state.period === "midday" ? 3 : 6;
  const scaledBusCount = Math.max(0, Math.round((baseBusCount * state.busLevel) / 100));

  for (let index = 0; index < scaledBusCount; index += 1) {
    const phase = ((timeSeconds / 3600) * 0.55 + index / Math.max(scaledBusCount, 1)) % 1;
    const forward = index % 2 === 0;
    const latlng = pointAlongPolyline(route, forward ? phase : 1 - phase);
    const marker = L.marker(latlng, {
      icon: L.divIcon({
        className: "",
        html: '<div class="bus-marker"></div>',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    });
    marker.bindTooltip("Presentasjonsbuss");
    marker.addTo(busLayer);
  }
}

function drawPedestrianPulses(timeSeconds) {
  pulseLayer.clearLayers();
  const networkMeta = manifest.networks[state.family] ?? manifest.networks.scenario_4A_base;
  const hotspots = networkMeta.pedestrian_hotspots ?? [];
  const baseLevel = state.pedestrianLevel / 100;
  const pulseStrength = state.pulseLevel / 100;
  const wave = pulseEnvelope(timeSeconds);

  for (const hotspot of hotspots) {
    const radius = 8 + baseLevel * 9 + pulseStrength * wave * 15;
    const opacity = clamp(0.2 + baseLevel * 0.18 + pulseStrength * wave * 0.32, 0.2, 0.9);
    const circle = L.circleMarker([hotspot.lat, hotspot.lon], {
      radius,
      color: "#d97706",
      weight: 1.5,
      fillColor: "#f59e0b",
      fillOpacity: opacity,
    });
    circle.bindTooltip(`${hotspot.label}: fotgjengerpuls`);
    circle.addTo(pulseLayer);
  }
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

  const busFactor = 1 + ((state.busLevel - 100) / 100) * manifest.synthetic.bus_penalty_per_100pct;
  const pedestrianFactor = 1 + ((state.pedestrianLevel - 100) / 100) * manifest.synthetic.pedestrian_penalty_per_100pct;
  const pulseFactor = 1 + (state.pulseLevel / 100) * manifest.synthetic.pulse_penalty_max * 0.45;
  const total = clamp(busFactor * pedestrianFactor * pulseFactor, 0.75, 4.2);

  result.avg_duration_min *= Math.max(total * 0.9, 0.7);
  result.system_delay_h *= total;
  result.queue_km *= Math.max(total * 0.95, 0.7);
  result.emergency_avg_min *= Math.max(1 + (total - 1) * 0.6, 0.8);

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

function isPedestrianHotspot(name) {
  return /Bernt Balchens vei|Rolfsbuktveien|Snarøyveien/.test(name);
}

function pulseEnvelope(timeSeconds) {
  const period = manifest.synthetic.pulse_period_s;
  const phase = (timeSeconds % period) / period;
  const distance = Math.min(Math.abs(phase - 0.1), 1 - Math.abs(phase - 0.1));
  return Math.exp(-Math.pow(distance / 0.12, 2));
}

function pointAlongPolyline(points, progress) {
  if (points.length === 0) {
    return [manifest.default_center[0], manifest.default_center[1]];
  }
  if (points.length === 1) {
    return points[0];
  }

  const lengths = [];
  let total = 0;
  for (let index = 1; index < points.length; index += 1) {
    const seg = distance(points[index - 1], points[index]);
    lengths.push(seg);
    total += seg;
  }
  let remaining = clamp(progress, 0, 1) * total;
  for (let index = 0; index < lengths.length; index += 1) {
    const seg = lengths[index];
    if (remaining <= seg) {
      const ratio = seg === 0 ? 0 : remaining / seg;
      return [
        points[index][0] + (points[index + 1][0] - points[index][0]) * ratio,
        points[index][1] + (points[index + 1][1] - points[index][1]) * ratio,
      ];
    }
    remaining -= seg;
  }
  return points[points.length - 1];
}

function distance(a, b) {
  const dx = b[1] - a[1];
  const dy = b[0] - a[0];
  return Math.sqrt(dx * dx + dy * dy);
}

function formatClock(timeSeconds, period) {
  const starts = {
    morning: [7, 45],
    midday: [12, 0],
    afternoon: [15, 30],
  };
  const [hour, minute] = starts[period] ?? [12, 0];
  const totalMinutes = hour * 60 + minute + Math.floor(timeSeconds / 60);
  const hh = String(Math.floor(totalMinutes / 60) % 24).padStart(2, "0");
  const mm = String(totalMinutes % 60).padStart(2, "0");
  return `${hh}:${mm}`;
}

function startPlayback() {
  if (state.isPlaying) {
    return;
  }
  state.isPlaying = true;
  ui.playPauseButton.textContent = "Pause";
  playTimer = window.setInterval(async () => {
    const mode = await resolveMode();
    const max = Math.max(getFrameCount(mode) - 1, 0);
    state.frameIndex = state.frameIndex >= max ? 0 : state.frameIndex + 1;
    await updateDynamicLayers(mode);
  }, 420);
}

function stopPlayback() {
  state.isPlaying = false;
  ui.playPauseButton.textContent = "Spill av";
  if (playTimer) {
    window.clearInterval(playTimer);
    playTimer = null;
  }
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

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Kunne ikke laste ${path}`);
  }
  return response.json();
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}
