import { buildSummarySeries, nearestSeriesPoint, rollingKpiAtTime } from "./data.js"
import { clamp, formatSigned } from "./utils.js"

export function renderComparisonTable({ manifest, state, ui, onSelectFamily }) {
  const period = state.period === "midday" ? "morning" : state.period
  const rows = manifest.families.map((family) => {
    const scenarioKey = `${family.id}_${period}`
    const kpis = manifest.scenarios[scenarioKey]?.kpis ?? {}
    return {
      id: family.id,
      label: family.label,
      travel_time: kpis.snaroya_avg_min ?? null,
      queue_km: kpis.queue_km ?? null,
      system_delay: kpis.system_delay_h ?? null,
      emergency: kpis.emergency_avg_min ?? null,
    }
  })

  const metrics = ["travel_time", "queue_km", "system_delay", "emergency"]
  const best = {}
  const worst = {}
  for (const metric of metrics) {
    const values = rows.map((row) => row[metric]).filter((value) => value != null)
    if (values.length > 0) {
      best[metric] = Math.min(...values)
      worst[metric] = Math.max(...values)
    }
  }

  const units = {
    travel_time: " min",
    queue_km: " km",
    system_delay: " t",
    emergency: " min",
  }

  ui.compareBody.innerHTML = ""
  for (const row of rows) {
    const tr = document.createElement("tr")
    if (row.id === state.family) {
      tr.classList.add("compare-active")
    }

    const tdLabel = document.createElement("td")
    tdLabel.textContent = row.label
    tr.appendChild(tdLabel)

    for (const metric of metrics) {
      const td = document.createElement("td")
      if (row[metric] != null) {
        const decimals = metric === "system_delay" ? 0 : 1
        td.textContent = `${row[metric].toFixed(decimals)}${units[metric]}`
        if (best[metric] != null && worst[metric] != null && best[metric] !== worst[metric]) {
          if (row[metric] === best[metric]) {
            td.classList.add("compare-best")
          } else if (row[metric] === worst[metric]) {
            td.classList.add("compare-worst")
          }
        }
      } else {
        td.textContent = "-"
      }
      tr.appendChild(td)
    }

    tr.style.cursor = "pointer"
    tr.addEventListener("click", () => {
      void onSelectFamily(row.id)
    })

    ui.compareBody.appendChild(tr)
  }
}

export function updateKpis({ manifest, mode, state, timeS, ui }) {
  const kpis = rollingKpiAtTime({ manifest, mode, state, timeS })
  ui.kpiFromSnaroya.textContent = kpis.snaroya_from != null ? `${kpis.snaroya_from.toFixed(1)} min` : "-"
  ui.kpiToSnaroya.textContent = kpis.snaroya_to != null ? `${kpis.snaroya_to.toFixed(1)} min` : "-"
  ui.kpiEmergency.textContent = kpis.emergency != null ? `${kpis.emergency.toFixed(1)} min` : "-"
  ui.kpiQueue.textContent = `${kpis.queue_km.toFixed(1)} km`
}

export function drawCharts({ manifest, mode, state, timeS, ui }) {
  const series = buildSummarySeries({ manifest, mode, state })
  const current = nearestSeriesPoint(series, timeS)
  ui.queueChartValue.textContent = current ? `${Math.round(current.queue)} kjt` : "0 kjt"
  ui.growthChartValue.textContent = current ? `${formatSigned(Math.round(current.growth))} kjt` : "0 kjt"
  drawSeriesChart(ui.queueTimelineChart, series, timeS, {
    stroke: "#fbcd5a",
    fill: "rgba(251, 205, 90, 0.16)",
    valueKey: "queue",
    baseline: 0,
  })
  drawSeriesChart(ui.queueGrowthChart, series, timeS, {
    stroke: "#73d2de",
    fill: "rgba(115, 210, 222, 0.16)",
    valueKey: "growth",
    baseline: 0,
  })
}

function drawSeriesChart(canvas, series, timeS, options) {
  const context = canvas.getContext("2d")
  if (!context) {
    return
  }

  const width = canvas.clientWidth || 300
  const height = canvas.clientHeight || 120
  const dpr = window.devicePixelRatio || 1
  canvas.width = Math.round(width * dpr)
  canvas.height = Math.round(height * dpr)
  context.setTransform(dpr, 0, 0, dpr, 0, 0)
  context.clearRect(0, 0, width, height)

  const padding = { top: 12, right: 12, bottom: 18, left: 12 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const baseline = options.baseline ?? 0
  const values = series.length ? series.map((point) => point[options.valueKey]) : [0]
  const minValue = Math.min(...values, baseline)
  const maxValue = Math.max(...values, baseline, 1)
  const valueSpan = Math.max(maxValue - minValue, 1)
  const maxTime = series.at(-1)?.t ?? 0

  context.strokeStyle = "rgba(255,255,255,0.14)"
  context.lineWidth = 1
  context.beginPath()
  context.moveTo(padding.left, padding.top + chartHeight)
  context.lineTo(padding.left + chartWidth, padding.top + chartHeight)
  context.stroke()

  if (!series.length) {
    return
  }

  const yForValue = (value) => padding.top + chartHeight - ((value - minValue) / valueSpan) * chartHeight
  const xForTime = (value) => padding.left + (maxTime > 0 ? (value / maxTime) * chartWidth : 0)
  const baselineY = yForValue(baseline)

  context.fillStyle = options.fill
  context.beginPath()
  context.moveTo(xForTime(series[0].t), baselineY)
  for (const point of series) {
    context.lineTo(xForTime(point.t), yForValue(point[options.valueKey]))
  }
  context.lineTo(xForTime(series.at(-1).t), baselineY)
  context.closePath()
  context.fill()

  context.strokeStyle = options.stroke
  context.lineWidth = 2
  context.beginPath()
  for (const [index, point] of series.entries()) {
    const x = xForTime(point.t)
    const y = yForValue(point[options.valueKey])
    if (index === 0) {
      context.moveTo(x, y)
    } else {
      context.lineTo(x, y)
    }
  }
  context.stroke()

  const playheadX = xForTime(clamp(timeS, 0, maxTime))
  context.strokeStyle = "rgba(255,255,255,0.88)"
  context.lineWidth = 1.25
  context.beginPath()
  context.moveTo(playheadX, padding.top)
  context.lineTo(playheadX, padding.top + chartHeight)
  context.stroke()
}