import { clamp, round1 } from "./utils.js"

const TILES = {
  light: {
    url: "https://cache.kartverket.no/v1/wmts/1.0.0/topograatone/default/webmercator/{z}/{y}/{x}.png",
    attribution: "&copy; Kartverket",
  },
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
}

export function createMapController({ manifest, ui, darkMode, popupRenderer = defaultEdgePopup, onEdgeSelected = null }) {
  const map = L.map("map", {
    zoomControl: true,
    minZoom: 12,
  })

  const activeTile = TILES[darkMode ? "dark" : "light"]
  let tileLayer = L.tileLayer(activeTile.url, {
    attribution: activeTile.attribution,
    maxZoom: 19,
    subdomains: "abcd",
  }).addTo(map)

  applyTheme(darkMode)
  map.fitBounds(manifest.default_bounds)

  map.on("moveend zoomend", () => {
    if (localStorage.getItem("debug") === "true") {
      const center = map.getCenter()
      const bounds = map.getBounds()
      console.debug("[map] center:", [center.lat, center.lng], "zoom:", map.getZoom())
      console.debug("[map] bounds:", [[bounds.getSouth(), bounds.getWest()], [bounds.getNorth(), bounds.getEast()]])
    }
  })

  let networkLayer = null
  let networkData = null
  let edgeLayers = new Map()
  let activeEdges = new Set()
  const anchorLayer = L.layerGroup().addTo(map)
  const entryPointLayer = L.layerGroup().addTo(map)
  const emergencyLayer = L.layerGroup().addTo(map)
  const vehicleLayer = L.layerGroup().addTo(map)
  const signalLayer = L.layerGroup().addTo(map)
  const roundaboutLayer = L.layerGroup().addTo(map)
  const labelLayer = L.layerGroup().addTo(map)
  const artifactLayer = L.layerGroup().addTo(map)
  const selectionLayer = L.layerGroup().addTo(map)

  function applyTheme(dark) {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light")
    ui.themeToggle.textContent = dark ? "🌙" : "☀️"
  }

  function toggleTheme(dark) {
    applyTheme(dark)
    const tile = TILES[dark ? "dark" : "light"]
    map.removeLayer(tileLayer)
    tileLayer = L.tileLayer(tile.url, {
      attribution: tile.attribution,
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(map)
  }

  async function ensureNetworkLoaded({ family, networkMeta, loadNetwork }) {
    if (networkLayer && networkLayer.familyId === family) {
      return
    }

    if (networkLayer) {
      map.removeLayer(networkLayer)
      edgeLayers = new Map()
      activeEdges = new Set()
    }

    const geojson = await loadNetwork(networkMeta.file)
    networkData = geojson
    networkLayer = L.geoJSON(geojson, {
      style: (feature) => baseEdgeStyle(feature.properties.lanes),
      onEachFeature: (feature, layer) => {
        edgeLayers.set(feature.properties.id, layer)
        layer.bindPopup(popupRenderer(feature))
        if (onEdgeSelected) {
          layer.on("click", () => onEdgeSelected(feature.properties.id))
        }
      },
    }).addTo(map)
    networkLayer.familyId = family
  }

  function syncVisualMode(mode, state) {
    const vehicleCapable = mode.kind === "real" && hasVehiclePlayback(mode.playback)
    ui.visualModeSelect.querySelector('option[value="vehicles"]').disabled = !vehicleCapable
    if (!vehicleCapable && state.visualMode === "vehicles") {
      state.visualMode = "edges"
      ui.visualModeSelect.value = "edges"
    }
  }

  function renderDynamicLayers(frame, state) {
    drawFrame(frame, state.visualMode)
    drawVehicles(frame, state)
    drawEmergency(frame, state)
  }

  function renderAnchors() {
    anchorLayer.clearLayers()
    for (const anchor of manifest.anchors ?? []) {
      const marker = L.marker([anchor.lat, anchor.lon], {
        icon: L.divIcon({
          className: "",
          html: '<div class="anchor-icon"></div>',
          iconSize: [16, 16],
          iconAnchor: [8, 8],
        }),
        interactive: false,
      }).addTo(anchorLayer)
      marker.bindTooltip(`<strong>${anchor.title}</strong>${anchor.detail}`, {
        permanent: true,
        direction: anchor.id === "south" ? "right" : "left",
        offset: anchor.id === "south" ? [14, 0] : [-14, 0],
        className: "anchor-tooltip",
      })
    }
  }

  function renderEntryPoints() {
    entryPointLayer.clearLayers()
    for (const ep of manifest.entry_points ?? []) {
      const bearing = ep.bearing ?? 0
      const arrowSvg =
        `<svg class="entry-arrow-svg" viewBox="0 0 40 40" width="36" height="36" ` +
        `style="transform:rotate(${bearing}deg);transform-origin:center center">` +
        `<path d="M20 4 L28 18 L23 18 L23 34 L17 34 L17 18 L12 18 Z" ` +
        `fill="#0d5c63" fill-opacity="0.85" stroke="#fff" stroke-width="1.5"/>` +
        `</svg>`
      const marker = L.marker([ep.lat, ep.lon], {
        icon: L.divIcon({
          className: "entry-point-marker",
          html: `<div class="entry-point-icon">${arrowSvg}</div>`,
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        }),
        interactive: true,
      }).addTo(entryPointLayer)
      const tooltipDir = { snaroya: "right", e18_west: "left", e18_east: "right", ring3_north: "left" }[ep.id] ?? "right"
      const tooltipOffset = tooltipDir === "right" ? [22, 0] : [-22, 0]
      marker.bindTooltip(`<strong>${ep.title}</strong>${ep.detail}`, {
        permanent: true,
        direction: tooltipDir,
        offset: tooltipOffset,
        className: "entry-point-tooltip",
      })
    }
  }

  function drawFrame(frame, visualMode) {
    if (visualMode === "vehicles") {
      resetEdgeStyling()
      return
    }
    const edges = frame.edges ?? {}
    const nextActive = new Set()

    for (const edgeId of activeEdges) {
      if (!edges[edgeId]) {
        const layer = edgeLayers.get(edgeId)
        if (layer) {
          layer.setStyle(baseEdgeStyle(layer.feature.properties.lanes))
        }
      }
    }

    for (const [edgeId, values] of Object.entries(edges)) {
      const layer = edgeLayers.get(edgeId)
      if (!layer) {
        continue
      }
      nextActive.add(edgeId)
      const props = layer.feature.properties
      const lanes = props.lanes || 1
      layer.setStyle(
        visualMode === "utilization"
          ? utilizationEdgeStyle(values[0], values[1], props.capacity_vph_estimate, lanes, values[2], values[3])
          : edgeStyle(values[0], values[1], lanes, values[2], values[3]),
      )
    }

    activeEdges = nextActive
  }

  function resetEdgeStyling() {
    for (const edgeId of activeEdges) {
      const layer = edgeLayers.get(edgeId)
      if (layer) {
        layer.setStyle(baseEdgeStyle(layer.feature.properties.lanes))
      }
    }
    activeEdges = new Set()
  }

  function drawEmergency(frame, state) {
    emergencyLayer.clearLayers()
    if (!state.showEmergency || state.visualMode === "vehicles") {
      return
    }

    for (const item of frame.emergency ?? []) {
      const marker = L.marker([item.lat, item.lon], {
        icon: L.divIcon({
          className: "",
          html: '<div class="emergency-marker"></div>',
          iconSize: [16, 16],
          iconAnchor: [8, 8],
        }),
        zIndexOffset: 10000,
      })
      marker.bindTooltip(`Blålys: ${item.speed.toFixed(0)} km/t`)
      marker.addTo(emergencyLayer)
    }
  }

  function drawVehicles(frame, state) {
    vehicleLayer.clearLayers()
    if (state.visualMode !== "vehicles") {
      return
    }
    if (state.frameIndex === 0 && !state.isPlaying) {
      return
    }

    const allVehicles = frame.vehicles ?? []
    const normalVehicles = []
    const emergencyVehicles = []
    for (const vehicle of allVehicles) {
      if (vehicle[4] === 1) {
        emergencyVehicles.push(vehicle)
      } else {
        normalVehicles.push(vehicle)
      }
    }

    for (const vehicle of [...normalVehicles, ...emergencyVehicles]) {
      const [, lat, lon, speedKmh, kind, angle = 0] = vehicle
      if (!state.showEmergency && kind === 1) {
        continue
      }
      const style = vehicleStyle(speedKmh, kind, map.getZoom())
      const marker = L.marker([lat, lon], {
        icon: L.divIcon({
          className: kind === 1 ? "vehicle-marker vehicle-marker-emergency" : "vehicle-marker",
          html: vehicleSvg(style, angle),
          iconSize: style.iconSize,
          iconAnchor: style.iconAnchor,
        }),
        zIndexOffset: kind === 1 ? 10000 : 0,
      }).addTo(vehicleLayer)
      if (kind === 1) {
        marker.bindTooltip(`Utrykningskjøretøy: ${Math.round(speedKmh)} km/t`, { direction: "top", offset: [0, -12] })
      } else if (speedKmh > 0) {
        marker.bindTooltip(`${Math.round(speedKmh)} km/t`, { direction: "top", offset: [0, -8] })
      }
    }
  }

  function getEdgeFeature(edgeId) {
    return edgeLayers.get(edgeId)?.feature ?? null
  }

  function getNetworkData() {
    return networkData
  }

  function renderAdvancedOverlays({
    showLabels = false,
    showSignals = false,
    showRoundabouts = false,
    edgeEdits = {},
    artifacts = [],
    selectedEdgeId = null,
  } = {}) {
    labelLayer.clearLayers()
    signalLayer.clearLayers()
    roundaboutLayer.clearLayers()
    artifactLayer.clearLayers()
    selectionLayer.clearLayers()

    if (!networkData) {
      return
    }

    if (showSignals) {
      for (const signal of networkData.meta?.signals ?? []) {
        L.circleMarker([signal.lat, signal.lon], {
          radius: 5,
          color: "#f97316",
          weight: 2,
          fillColor: "#fff7ed",
          fillOpacity: 0.92,
        })
          .bindTooltip(`Signal ${signal.id}`, { direction: "top", offset: [0, -10] })
          .addTo(signalLayer)
      }
    }

    if (showRoundabouts) {
      for (const roundabout of networkData.meta?.roundabouts ?? []) {
        const coords = (roundabout.coordinates ?? []).map(([lon, lat]) => [lat, lon])
        if (coords.length > 2) {
          L.polygon(coords, {
            color: "#14b8a6",
            weight: 2,
            fillColor: "#2dd4bf",
            fillOpacity: 0.08,
            interactive: false,
            dashArray: "6 4",
          }).addTo(roundaboutLayer)
        }
        const [lon, lat] = roundabout.center ?? [0, 0]
        L.marker([lat, lon], {
          icon: L.divIcon({
            className: "roundabout-label-marker",
            html: `<span class="mini-map-label">${roundabout.label}</span>`,
          }),
          interactive: false,
        }).addTo(roundaboutLayer)
      }
    }

    if (showLabels) {
      for (const feature of networkData.features ?? []) {
        const [lon, lat] = feature.properties.midpoint ?? midpointFromCoords(feature.geometry.coordinates)
        L.marker([lat, lon], {
          icon: L.divIcon({
            className: "edge-label-marker",
            html: `<span class="mini-map-label">${feature.properties.name}</span>`,
          }),
          interactive: false,
        }).addTo(labelLayer)
      }
    }

    for (const edgeId of Object.keys(edgeEdits)) {
      const feature = getEdgeFeature(edgeId)
      if (!feature) {
        continue
      }
      L.polyline(toLeafletCoords(feature.geometry.coordinates), {
        color: edgeId === selectedEdgeId ? "#f97316" : "#7c3aed",
        weight: edgeId === selectedEdgeId ? 8 : 6,
        opacity: 0.55,
        interactive: false,
      }).addTo(selectionLayer)
    }

    if (selectedEdgeId && !edgeEdits[selectedEdgeId]) {
      const feature = getEdgeFeature(selectedEdgeId)
      if (feature) {
        L.polyline(toLeafletCoords(feature.geometry.coordinates), {
          color: "#f97316",
          weight: 8,
          opacity: 0.55,
          interactive: false,
        }).addTo(selectionLayer)
      }
    }

    for (const artifact of artifacts) {
      renderArtifact(artifact)
    }
  }

  function renderArtifact(artifact) {
    const feature = getEdgeFeature(artifact.edge_id)
    if (!feature) {
      return
    }

    if (artifact.type === "crossing") {
      const [lon, lat] = feature.properties.to_node_coord ?? feature.properties.midpoint ?? midpointFromCoords(feature.geometry.coordinates)
      L.marker([lat, lon], {
        icon: L.divIcon({
          className: "artifact-crossing-marker",
          html: '<div class="artifact-crossing-icon"></div>',
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        }),
      })
        .bindTooltip("Planlagt kryssing", { direction: "top", offset: [0, -8] })
        .addTo(artifactLayer)
      return
    }

    const style = artifactStyle(artifact.type)
    L.polyline(toLeafletCoords(feature.geometry.coordinates), {
      color: style.color,
      weight: style.weight,
      opacity: style.opacity,
      dashArray: style.dashArray,
      interactive: false,
    }).addTo(artifactLayer)
  }

  return {
    map,
    toggleTheme,
    ensureNetworkLoaded,
    syncVisualMode,
    renderDynamicLayers,
    renderAnchors,
    renderEntryPoints,
    renderAdvancedOverlays,
    getEdgeFeature,
    getNetworkData,
  }
}

function defaultEdgePopup(feature) {
  return `<strong>${feature.properties.name}</strong><br/>` +
    `Felter: ${feature.properties.lanes}<br/>` +
    `Skiltet fart: ${feature.properties.speed_kmh} km/t`
}

function hasVehiclePlayback(playback) {
  return Boolean(
    playback?.frames?.some((frame) => Array.isArray(frame.vehicles) && frame.vehicles.length > 0),
  )
}

function baseEdgeStyle(lanes = 1) {
  return {
    color: "#a8b7b3",
    weight: 1.2 + lanes * 0.45,
    opacity: 0.55,
  }
}

function edgeStyle(count, speedKmh, lanes, emergencyCount, eventCount) {
  const loadPerLane = count / Math.max(lanes, 1)
  const severity = clamp(loadPerLane / 5 + Math.max(0, 28 - speedKmh) / 28, 0, 1.4)
  const hue = clamp(170 - severity * 150, 10, 170)
  const lightness = clamp(48 - severity * 10, 28, 52)
  const saturation = eventCount > 0 ? 82 : 74
  return {
    color: `hsl(${hue} ${saturation}% ${lightness}%)`,
    weight: 1.4 + Math.min(loadPerLane, 6) * 0.9 + emergencyCount * 0.4,
    opacity: 0.92,
  }
}

function utilizationEdgeStyle(count, speedKmh, capacityEstimate, lanes, emergencyCount, eventCount) {
  const capacityUnits = Math.max((capacityEstimate ?? lanes * 900) / 120, lanes * 6, 1)
  const utilization = clamp(count / capacityUnits, 0, 1.6)
  const speedPenalty = clamp((25 - speedKmh) / 25, 0, 1)
  const severity = clamp(utilization * 0.8 + speedPenalty * 0.45, 0, 1.4)
  const hue = clamp(145 - severity * 135, 8, 145)
  const lightness = clamp(50 - severity * 12, 22, 50)
  return {
    color: `hsl(${hue} 82% ${lightness}%)`,
    weight: 1.6 + Math.min(lanes, 5) * 0.9 + emergencyCount * 0.4 + eventCount * 0.2,
    opacity: 0.94,
  }
}

function vehicleStyle(speedKmh, kind, zoom) {
  const scale = clamp(Math.pow(1.8, zoom - 15), 0.72, 2.2) * 0.75
  if (kind === 1) {
    return {
      color: "#facc15",
      opacity: 0.98,
      shape: "emergency",
      iconSize: [Math.round(22 * scale), Math.round(36 * scale)],
      iconAnchor: [Math.round(11 * scale), Math.round(18 * scale)],
    }
  }
  if (kind === 2) {
    return {
      color: "#f59e0b",
      opacity: 0.92,
      shape: "event",
      iconSize: [Math.round(16 * scale), Math.round(26 * scale)],
      iconAnchor: [Math.round(8 * scale), Math.round(13 * scale)],
    }
  }
  const hue = clamp(speedKmh * 3, 5, 120)
  const stopped = speedKmh < 8
  return {
    color: `hsl(${hue} 78% 52%)`,
    opacity: stopped ? 0.92 : 0.84,
    shape: "car",
    iconSize: [Math.round((stopped ? 15 : 13) * scale), Math.round((stopped ? 28 : 24) * scale)],
    iconAnchor: [Math.round((stopped ? 7.5 : 6.5) * scale), Math.round((stopped ? 14 : 12) * scale)],
  }
}

function vehicleSvg(style, angle) {
  const rotation = Number.isFinite(angle) ? angle : 0
  if (style.shape === "emergency") {
    const phase = Math.floor(Date.now() / 250) % 2 === 0
    const leftFill = phase ? "#2563eb" : "#1e3a8a"
    const leftOpacity = phase ? 1 : 0.25
    const rightFill = phase ? "#1e3a8a" : "#2563eb"
    const rightOpacity = phase ? 0.25 : 1
    const glowT = (Math.sin(Date.now() / 160) + 1) / 2
    const glowR = Math.round(8 + glowT * 12)
    const glowA = (0.5 + glowT * 0.4).toFixed(2)
    const glowFilter =
      `drop-shadow(0 0 ${glowR}px rgba(37,99,235,${glowA})) ` +
      `drop-shadow(0 0 ${glowR * 2}px rgba(37,99,235,${(glowA * 0.5).toFixed(2)}))`
    return (
      `<svg class="vehicle-svg vehicle-svg-emergency" viewBox="0 0 20 36" width="${style.iconSize[0]}" height="${style.iconSize[1]}" ` +
      `style="transform:rotate(${rotation}deg);transform-origin:center center;filter:${glowFilter}">` +
      `<path class="vehicle-body" d="M6 2h8l3 7v18l-3 7H6l-3-7V9z" style="--vehicle-color:${style.color};--vehicle-opacity:${style.opacity}"/>` +
      `<rect class="vehicle-cabin" x="6.5" y="8" width="7" height="11" rx="2"/>` +
      `<rect class="vehicle-lightbar-left" x="5" y="3.5" width="5" height="3" rx="1.2" style="fill:${leftFill};opacity:${leftOpacity}"/>` +
      `<rect class="vehicle-lightbar-right" x="10" y="3.5" width="5" height="3" rx="1.2" style="fill:${rightFill};opacity:${rightOpacity}"/>` +
      `<path class="vehicle-nose" d="M8 2h4v2H8z"/>` +
      `</svg>`
    )
  }
  if (style.shape === "event") {
    return (
      `<svg class="vehicle-svg" viewBox="0 0 20 34" width="${style.iconSize[0]}" height="${style.iconSize[1]}" ` +
      `style="transform:rotate(${rotation}deg);transform-origin:center center">` +
      `<path class="vehicle-body" d="M5 2h10l3 6v18l-3 6H5l-3-6V8z" style="--vehicle-color:${style.color};--vehicle-opacity:${style.opacity}"/>` +
      `<rect class="vehicle-cabin" x="6" y="8" width="8" height="10" rx="2"/>` +
      `<path class="vehicle-nose" d="M8 3h4v2H8z"/>` +
      `</svg>`
    )
  }
  return (
    `<svg class="vehicle-svg" viewBox="0 0 18 32" width="${style.iconSize[0]}" height="${style.iconSize[1]}" ` +
    `style="transform:rotate(${rotation}deg);transform-origin:center center">` +
    `<path class="vehicle-body" d="M5 2h8l3 6v16l-3 6H5l-3-6V8z" style="--vehicle-color:${style.color};--vehicle-opacity:${style.opacity}"/>` +
    `<rect class="vehicle-cabin" x="5.5" y="8" width="7" height="9" rx="2"/>` +
    `<path class="vehicle-nose" d="M7 3h4v2H7z"/>` +
    `</svg>`
  )
}

function midpointFromCoords(coords) {
  if (!coords?.length) {
    return [0, 0]
  }
  return coords[Math.floor(coords.length / 2)]
}

function toLeafletCoords(coords) {
  return (coords ?? []).map(([lon, lat]) => [lat, lon])
}

function artifactStyle(type) {
  switch (type) {
    case "cycleway":
      return { color: "#2563eb", weight: 5, opacity: 0.9, dashArray: "8 6" }
    case "sidewalk":
      return { color: "#f59e0b", weight: 4, opacity: 0.88, dashArray: "2 6" }
    case "median":
      return { color: "#111827", weight: 3, opacity: 0.78, dashArray: "10 4" }
    default:
      return { color: "#94a3b8", weight: 3, opacity: 0.8, dashArray: "4 4" }
  }
}