# Implementation Plan: Model Gap Closures

Date: 2026-03-15

Source: QA_FINDINGS_CHAT.md (action group analysis) + QA_FINDINGS.md (Flytårnet junction)

## Approach

Each gap is implemented as a standalone commit. Gaps are ordered by
impact-to-effort ratio, starting with the highest. Each commit modifies
the relevant scripts and reruns only the affected scenarios where feasible.

## Gap 1: Emergency vehicle response time metric

**Why:** The single most emotionally resonant argument in the action group chat.
An ambulance stuck in traffic on the only road to Snarøya is visceral and
politically powerful. Quantifying the response time delta between 2+3 and 2+2
lanes gives the group a concrete number.

**What:**
- Add a `vType` with `vClass="emergency"` and blue-light behavior to the demand generator
- Insert 3 emergency vehicles at random intervals during peak hour (one every ~20 min)
- Route them from `snv_syd` (Snarøya) to `snv_nordost` (nordre rundkjøring / hospital direction)
- Extract their travel times from tripinfo.xml separately from regular traffic
- Report the delta: emergency response time under base vs V1 conditions

**Files:** `scripts/03_generate_demand.py`, `scripts/04_run_simulation.py`, `scripts/06_generate_report.py`

---

## Gap 2: Per-capita delay metric (Snarøya residents only)

**Why:** The Bygdøy comparison argument. Snarøya has ~4,000 residents today scaling
to serve 40,000+ Fornebu residents. Per-capita delay isolates the impact on
Snarøya residents specifically, not through-traffic.

**What:**
- Filter tripinfo.xml for trips originating from `snv_syd` (Snarøya-bound zone)
- Compute mean delay per Snarøya-origin trip vs overall mean
- Add to report as a separate metric

**Files:** `scripts/04_run_simulation.py`, `scripts/06_generate_report.py`

---

## Gap 3: Queue length in km

**Why:** The action group cites "3.9 km queues out to E18" from the Aimsun model.
Our model shows 205-945 "not inserted" vehicles but doesn't translate that to a
distance metric people can visualize.

**What:**
- Post-process the "not inserted" + "waiting" vehicle counts
- Convert to approximate queue length: `queue_km = vehicles / density`
  where density ≈ 120 veh/km for stopped single-lane traffic
- Add queue_length_km to run_stats and report

**Files:** `scripts/04_run_simulation.py`, `scripts/06_generate_report.py`

---

## Gap 4: Rolfsbuktveien miljøgate variant

**Why:** The kommunestyre voted to convert Rolfsbuktveien to a "miljøgate".
This removes the only alternative route, forcing all traffic through Snarøyveien.
A compound scenario (V1 + Rolfsbukt restriction) shows the combined risk.

**What:**
- Add a new scenario family `scenario_4A_v1_rolfsbukt` that uses the V1 network
  with Rolfsbuktveien speed halved (15 km/h) via an additional file
- Create the additional file that restricts Rolfsbuktveien edges
- Run both AM and PM periods

**Files:** `scripts/utils/scenario_catalog.py`, `scripts/02_build_network.py` (or standalone generator), `scripts/05_analyze_results.py`, `scripts/06_generate_report.py`

---

## Gap 5: Unity Arena event-overlay demand

**Why:** Event nights at Unity Arena (up to 27,500 attendees) superimpose
thousands of additional vehicles on top of PM peak traffic. The group
repeatedly cites event-night gridlock.

**Demand model (corrected per user input):**
- **Capacity:** 27,500 attendees
- **Inbound (16:00-18:00):** Doors open ~18:00, cars arrive 16:00-18:00.
  Assume ~1/3 of attendees arrive by car (avg 2.5 per car) ≈ 3,667 vehicles.
  Of these, ~1/3 park (1,222 vehicles stay), ~2/3 are drop-offs (2,445 leave).
- **Drop-off outbound (16:00-18:00):** 2,445 vehicles leave after dropping off.
- **Return pickups (22:45-23:30):** ~1/3 of original inbound = 1,222 pickup
  vehicles reappear.
- **Parked departures (22:45-23:30):** ~1,222 vehicles leave from parking.
- All event traffic originates from/destined to nordre rundkjøring (E18).
- The PM simulation window (15:30-16:30) captures the leading edge of inbound
  event traffic overlapping with commuter rush.

**Files:** `scripts/03_generate_demand.py`, `scripts/utils/scenario_catalog.py`

---

## Gaps deferred (require Flytårnet junction model first)

- **Venstresvingefelt at Bernt Balchens / Martin Linges** — requires signal model
- **Future signalized søndre rundkjøring** — requires junction retype + TLL
- **E18 network extension** — high effort, low immediate value

## Execution order

```
Gap 1 → commit → Gap 2 → commit → Gap 3 → commit → Gap 4 → commit → Gap 5 → commit
```

After all five: rerun full simulation suite, regenerate charts and report.
