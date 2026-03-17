export function lerp(a, b, t) {
  return a + (b - a) * t
}

export function lerpAngle(a, b, t) {
  const delta = ((b - a + 540) % 360) - 180
  return (a + delta * t + 360) % 360
}

export function round1(value) {
  return Math.round(value * 10) / 10
}

export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

export function formatSigned(value) {
  if (value > 0) {
    return `+${value}`
  }
  return String(value)
}

export function formatClock(timeSeconds, period) {
  const starts = {
    morning: [7, 45],
    midday: [12, 0],
    afternoon: [15, 30],
  }
  const [hour, minute] = starts[period] ?? [12, 0]
  const startSeconds = hour * 3600 + minute * 60
  const totalSeconds = Math.max(0, Math.floor(startSeconds + timeSeconds))
  const hh = String(Math.floor(totalSeconds / 3600) % 24).padStart(2, "0")
  const mm = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0")
  const ss = String(totalSeconds % 60).padStart(2, "0")
  return `${hh}:${mm}:${ss}`
}