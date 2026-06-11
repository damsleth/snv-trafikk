import { afterEach, describe, expect, it, vi } from "vitest"

import { buildFrame, fetchJson, getFrameCount, loadPlayback } from "../modules/data.js"

afterEach(() => {
  vi.restoreAllMocks()
})

describe("fetchJson", () => {
  it("loads JSON responses", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })))

    await expect(fetchJson("./demo.json")).resolves.toEqual({ ok: true })
  })

  it("reports HTTP failures", async () => {
    const onError = vi.fn()
    vi.stubGlobal("fetch", vi.fn(async () => new Response("missing", { status: 404 })))

    await expect(fetchJson("./missing.json", { onError })).rejects.toThrow("Kunne ikke laste")
    expect(onError).toHaveBeenCalledWith("Kunne ikke laste ./missing.json")
  })
})

describe("loadPlayback", () => {
  it("does not keep failed playback promises in cache", async () => {
    const cache = { playbacks: new Map() }
    const manifest = { scenarios: { demo: { playback: { file: "data/playback/demo.json" } } } }
    vi.stubGlobal("fetch", vi.fn(async () => new Response("missing", { status: 404 })))

    await expect(loadPlayback(manifest, "demo", cache)).rejects.toThrow()
    expect(cache.playbacks.has("data/playback/demo.json")).toBe(false)
  })
})

describe("frame helpers", () => {
  it("interpolates real playback frames", () => {
    const mode = {
      kind: "real",
      playback: {
        frames: [
          { t: 0, edges: { a: [1, 10, 0, 0] }, emergency: [], vehicles: [["v1", 59, 10, 10, 0, 0]] },
          { t: 10, edges: { a: [3, 30, 0, 0] }, emergency: [], vehicles: [["v1", 60, 11, 20, 0, 90]] },
        ],
      },
    }

    expect(getFrameCount(mode)).toBe(2)
    const frame = buildFrame({ manifest: {}, state: {}, mode, index: 0, progress: 0.5 })
    expect(frame.time_s).toBe(5)
    expect(frame.edges.a[0]).toBe(2)
    expect(frame.vehicles[0][1]).toBe(59.5)
  })
})
