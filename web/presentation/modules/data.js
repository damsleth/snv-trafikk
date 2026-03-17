import { clamp, lerp, lerpAngle, round1 } from "./utils.js"

export async function fetchJson(path, { onError } = {}) {
  const response = await fetch(path)
  if (!response.ok) {
    const error = new Error(`Kunne ikke laste ${path}`)
    onError?.(error.message)
    throw error
  }
  return response.json()
}

export async function loadManifest() {
  try {
    return await fetchJson("./data/manifest.json")
  } catch (error) {
    document.body.innerHTML = `<main class="app-error"><h1>Presentasjonen kunne ikke lastes</h1><p>${error.message}</p></main>`
    throw error
  }
}

export async function loadNetwork(path, cache, { onError } = {}) {
  if (!cache.networks.has(path)) {
    cache.networks.set(path, fetchJson(`./${path}`, { onError }))
  }
  return cache.networks.get(path)
}

export async function loadPlayback(manifest, scenarioName, cache, { onError } = {}) {
  const scenario = manifest.scenarios[scenarioName]
  if (!scenario) {
    return { frames: [], interval_s: 15 }
  }
  const key = scenario.playback.file
  if (!cache.playbacks.has(key)) {
    cache.playbacks.set(key, fetchJson(`./${key}`, { onError }))
  }
  return cache.playbacks.get(key)
}

export async function resolveMode({ manifest, state, cache, onError }) {
  if (state.period === "midday") {
    const morning = await loadPlayback(manifest, `${state.family}_morning`, cache, { onError })
    const afternoon = await loadPlayback(manifest, `${state.family}_afternoon`, cache, { onError })
    return {
      kind: "synthetic_midday",
      family: state.family,
      morning,
      afternoon,
    }
  }

  if (state.concert && state.period === "afternoon") {
    const eventScenario = `${state.family}_event_afternoon`
    const baseScenario = `${state.family}_afternoon`
    if (manifest.scenarios[eventScenario]) {
      return {
        kind: "real",
        scenario: eventScenario,
        playback: await loadPlayback(manifest, eventScenario, cache, { onError }),
      }
    }
    return {
      kind: "real_with_estimate",
      scenario: baseScenario,
      playback: await loadPlayback(manifest, baseScenario, cache, { onError }),
    }
  }

  const scenario = `${state.family}_${state.period}`
  return {
    kind: "real",
    scenario,
    playback: await loadPlayback(manifest, scenario, cache, { onError }),
  }
}

export function getFrameCount(mode) {
  if (mode.kind === "synthetic_midday") {
    return Math.min(mode.morning.frames.length, mode.afternoon.frames.length)
  }
  return mode.playback?.frames?.length ?? 0
}

export function getFrameDurationMs(mode) {
  if (mode.kind === "synthetic_midday") {
    return (mode.morning?.interval_s ?? 5) * 1000
  }
  return (mode.playback?.interval_s ?? 5) * 1000
}

export function hasVehiclePlayback(playback) {
  return Boolean(
    playback?.frames?.some((frame) => Array.isArray(frame.vehicles) && frame.vehicles.length > 0),
  )
}

export function buildFrame({ manifest, state, mode, index, progress = 0 }) {
  if (mode.kind === "synthetic_midday") {
    return buildSyntheticMiddayFrame(manifest, mode, index)
  }
  const playback = mode.playback ?? { frames: [], interval_s: 5 }
  const frame = playback.frames[index] ?? playback.frames[0] ?? { t: 0, edges: {}, emergency: [], vehicles: [] }
  const nextIndex = Math.min(index + 1, Math.max(playback.frames.length - 1, 0))
  const nextFrame = playback.frames[nextIndex] ?? frame
  const interpolated = interpolateRealFrame(frame, nextFrame, progress)
  const adjusted = applyConcertStress(manifest, state, mode, interpolated)
  return {
    time_s: lerp(frame.t, nextFrame.t ?? frame.t, progress),
    edges: adjusted.edges,
    emergency: adjusted.emergency,
    vehicles: adjusted.vehicles ?? interpolated.vehicles ?? [],
  }
}

export function rollingKpiAtTime({ manifest, mode, state, timeS }) {
  if (mode.kind === "synthetic_midday") {
    const morning = nearestRollingEntry(mode.morning?.rolling_kpis ?? [], timeS)
    const afternoon = nearestRollingEntry(mode.afternoon?.rolling_kpis ?? [], timeS)
    const factors = manifest.synthetic.midday_factor
    return {
      snaroya_from: scaledAverage(morning?.snaroya_from, afternoon?.snaroya_from, factors.avg_duration),
      snaroya_to: scaledAverage(morning?.snaroya_to, afternoon?.snaroya_to, factors.avg_duration),
      emergency: scaledAverage(morning?.emergency, afternoon?.emergency, factors.emergency),
      queue_km: round1((((morning?.queue_km ?? 0) + (afternoon?.queue_km ?? 0)) / 2) * factors.queue),
    }
  }

  const rolling = mode.playback?.rolling_kpis
  if (!rolling || rolling.length === 0) {
    return fallbackStaticKpis(manifest, mode, state)
  }

  const entry = nearestRollingEntry(rolling, timeS)
  const eventStress = getEventStress(manifest, state, mode)
  return {
    snaroya_from: scaleMaybe(entry?.snaroya_from, eventStress.avgDuration),
    snaroya_to: scaleMaybe(entry?.snaroya_to, eventStress.avgDuration),
    emergency: scaleMaybe(entry?.emergency, eventStress.emergency),
    queue_km: round1((entry?.queue_km ?? 0) * eventStress.queue),
  }
}

export function buildSummarySeries({ manifest, mode, state }) {
  if (mode.kind === "synthetic_midday") {
    const morning = mode.morning?.summary?.queue ?? []
    const afternoon = mode.afternoon?.summary?.queue ?? []
    const length = Math.min(morning.length, afternoon.length)
    const series = []
    for (let index = 0; index < length; index += 1) {
      const a = morning[index]
      const b = afternoon[index]
      const queue = ((a?.[3] ?? 0) + (b?.[3] ?? 0)) / 2 * manifest.synthetic.midday_factor.queue
      const waiting = ((a?.[1] ?? 0) + (b?.[1] ?? 0)) / 2 * manifest.synthetic.midday_factor.queue
      const halting = ((a?.[2] ?? 0) + (b?.[2] ?? 0)) / 2 * manifest.synthetic.midday_factor.queue
      series.push({
        t: a?.[0] ?? b?.[0] ?? 0,
        waiting,
        halting,
        queue,
        growth: 0,
      })
    }
    return withGrowth(series)
  }

  const baseSeries = (mode.playback?.summary?.queue ?? []).map((row) => ({
    t: row[0],
    waiting: row[1],
    halting: row[2],
    queue: row[3],
    growth: row[4],
  }))

  const eventStress = getEventStress(manifest, state, mode)
  if (eventStress.queue === 1) {
    return baseSeries
  }

  return withGrowth(
    baseSeries.map((point) => ({
      ...point,
      waiting: point.waiting * eventStress.queue,
      halting: point.halting * eventStress.queue,
      queue: point.queue * eventStress.queue,
    })),
  )
}

export function nearestSeriesPoint(series, timeS) {
  if (!series.length) {
    return null
  }
  const interval = Math.max(series[1]?.t - series[0]?.t || 5, 1)
  const index = clamp(Math.round(timeS / interval), 0, series.length - 1)
  return series[index]
}

function buildSyntheticMiddayFrame(manifest, mode, index) {
  const morningFrame = mode.morning.frames[index] ?? mode.morning.frames[0]
  const afternoonFrame = mode.afternoon.frames[index] ?? mode.afternoon.frames[0]
  const factor = manifest.synthetic.midday_factor.edge_load
  const edges = {}
  const union = new Set([
    ...Object.keys(morningFrame?.edges ?? {}),
    ...Object.keys(afternoonFrame?.edges ?? {}),
  ])

  for (const edgeId of union) {
    const a = morningFrame?.edges?.[edgeId] ?? [0, 0, 0, 0]
    const b = afternoonFrame?.edges?.[edgeId] ?? [0, 0, 0, 0]
    const count = Math.round(((a[0] + b[0]) / 2) * factor)
    const speed = round1(((a[1] + b[1]) / 2) * 1.08)
    const emergencyCount = Math.round((a[2] + b[2]) / 2)
    edges[edgeId] = [count, speed, emergencyCount, 0]
  }

  const syntheticFrame = {
    t: morningFrame?.t ?? afternoonFrame?.t ?? 0,
    edges,
    emergency: morningFrame?.emergency ?? [],
    vehicles: [],
  }
  return {
    time_s: syntheticFrame.t,
    edges: syntheticFrame.edges,
    emergency: syntheticFrame.emergency,
    vehicles: syntheticFrame.vehicles,
  }
}

function applyConcertStress(manifest, state, mode, frame) {
  const edges = {}
  const totalMultiplier = clamp(getEventStress(manifest, state, mode).systemDelay, 0.65, 6)

  for (const [edgeId, values] of Object.entries(frame.edges ?? {})) {
    const count = Math.max(0, Math.round(values[0] * totalMultiplier))
    const speed = Math.max(2, round1(values[1] / Math.max(totalMultiplier * 0.82, 0.85)))
    edges[edgeId] = [count, speed, values[2], values[3]]
  }

  return {
    edges,
    emergency: frame.emergency ?? [],
    vehicles: frame.vehicles ?? [],
  }
}

function interpolateRealFrame(frame, nextFrame, progress) {
  const ratio = clamp(progress, 0, 1)
  const edges = {}
  const edgeIds = new Set([
    ...Object.keys(frame.edges ?? {}),
    ...Object.keys(nextFrame.edges ?? {}),
  ])

  for (const edgeId of edgeIds) {
    const a = frame.edges?.[edgeId] ?? [0, 0, 0, 0]
    const b = nextFrame.edges?.[edgeId] ?? a
    edges[edgeId] = [
      Math.round(lerp(a[0], b[0], ratio)),
      round1(lerp(a[1], b[1], ratio)),
      Math.round(lerp(a[2], b[2], ratio)),
      Math.round(lerp(a[3], b[3], ratio)),
    ]
  }

  const currentVehicles = new Map((frame.vehicles ?? []).map((vehicle) => [vehicle[0], vehicle]))
  const nextVehicles = new Map((nextFrame.vehicles ?? []).map((vehicle) => [vehicle[0], vehicle]))
  const vehicles = []

  for (const [vehicleId, vehicle] of currentVehicles) {
    const nextVehicle = nextVehicles.get(vehicleId)
    if (!nextVehicle) {
      vehicles.push(vehicle)
      continue
    }
    vehicles.push([
      vehicleId,
      lerp(vehicle[1], nextVehicle[1], ratio),
      lerp(vehicle[2], nextVehicle[2], ratio),
      lerp(vehicle[3], nextVehicle[3], ratio),
      vehicle[4],
      lerpAngle(vehicle[5], nextVehicle[5], ratio),
    ])
  }

  return {
    edges,
    emergency: ratio < 0.5 ? frame.emergency ?? [] : nextFrame.emergency ?? [],
    vehicles,
  }
}

function withGrowth(series) {
  let previousQueue = null
  return series.map((point) => {
    const growth = previousQueue == null ? 0 : point.queue - previousQueue
    previousQueue = point.queue
    return { ...point, growth }
  })
}

function nearestRollingEntry(rolling, timeS) {
  if (!rolling?.length) {
    return null
  }
  let lo = 0
  let hi = rolling.length - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (rolling[mid].t <= timeS) {
      lo = mid
    } else {
      hi = mid - 1
    }
  }
  return rolling[lo]
}

function fallbackStaticKpis(manifest, mode, state) {
  const scenarioKpis = manifest.scenarios[mode.scenario]?.kpis ?? {}
  const eventStress = getEventStress(manifest, state, mode)
  return {
    snaroya_from: scaleMaybe(scenarioKpis.snaroya_avg_min ?? null, eventStress.avgDuration),
    snaroya_to: scaleMaybe(scenarioKpis.snaroya_avg_min ?? null, eventStress.avgDuration),
    emergency: scaleMaybe(scenarioKpis.emergency_avg_min ?? null, eventStress.emergency),
    queue_km: round1((scenarioKpis.queue_km ?? 0) * eventStress.queue),
  }
}

function getEventStress(manifest, state, mode) {
  if (!(state.concert && state.period === "afternoon")) {
    return { avgDuration: 1, systemDelay: 1, queue: 1, emergency: 1 }
  }
  if (mode.kind === "real" && manifest.scenarios[mode.scenario]?.has_event_overlay) {
    return { avgDuration: 1, systemDelay: 1, queue: 1, emergency: 1 }
  }
  const mapping = {
    scenario_4A_base: "base",
    scenario_4A_v1: "v1",
  }
  const key = mapping[state.family]
  const multipliers = key
    ? manifest.synthetic.event_multipliers[key]
    : manifest.synthetic.fallback_event_multipliers
  return {
    avgDuration: multipliers.avg_duration,
    systemDelay: multipliers.system_delay,
    queue: multipliers.queue,
    emergency: multipliers.emergency,
  }
}

function scaleMaybe(value, multiplier) {
  return value == null ? null : round1(value * multiplier)
}

function scaledAverage(a, b, multiplier) {
  if (a == null && b == null) {
    return null
  }
  return round1((((a ?? b ?? 0) + (b ?? a ?? 0)) / 2) * multiplier)
}