# Scenario Assumptions

This document is the human-readable companion to `scripts/utils/scenario_catalog.py`. The catalog is the executable source of truth; this file explains how the scenario families should be interpreted.

## Scenario Status Labels

- `main`: primary 4A comparison scenarios used for the KDP3 lane-variant story.
- `reference`: 1A/current-parking-norm reference scenarios for comparison with the official appendix demand level.
- `sensitivity`: parameter sensitivity checks, not policy forecasts.
- `exploratory`: useful stress tests or local hypotheses that need extra validation before public decision use.

## Main Comparison Scenarios

| Family | Status | Demand | Network | Purpose |
|---|---|---|---|---|
| `scenario_4A_base` | main | PGF 4A | current 2+3 profile | Reference for tightened parking norm/full buildout. |
| `scenario_4A_v1` | main | PGF 4A | V1/KDP3 2+2 profile | Main proposed bygate comparison against base. |
| `scenario_4A_v2` | main | PGF 4A | V2 lower-capacity variant | Lane-variant sensitivity within the main comparison set. |
| `scenario_4A_v3` | main | PGF 4A | V3 hybrid variant | Lane-variant sensitivity within the main comparison set. |

Main scenarios should be run with multiple seeds and reported as mean ± standard deviation.

## Reference Scenarios

`scenario_1A_base` and `scenario_1A_v1` use PGF scenario 1A demand, representing full buildout with current parking norm. They are useful as a demand-level reference, but the published KDP3 narrative should clearly distinguish them from the 4A main comparison.

## 80 Percent Demand Scaling

`scenario_4A_base_scaled80` and `scenario_4A_v1_scaled80` are sensitivity tests. They answer: what happens if the same OD pattern is uniformly scaled to 80 percent?

They should not be described as a validated policy forecast unless a separate policy analysis supports why that reduction is realistic. The scaling algorithm preserves rounded matrix totals through largest remainder allocation; see `scripts/03_generate_demand.py`.

## Event and Concert Scenarios

`scenario_4A_base_event` and `scenario_4A_v1_event` add an exploratory Unity Arena event overlay in the afternoon period. These scenarios are stress tests, not calibrated event forecasts. They should be presented with a clear caveat until real event traffic data is available.

## Rolfsbukt/Miljøgate Variant

`scenario_4A_v1_rolfsbukt` combines V1 with Rolfsbuktveien miljøgate assumptions. Treat it as exploratory unless the network changes and demand routing are separately validated.

## OSM Snapshot Policy

`network/osm/fornebu.osm.xml` is the model source snapshot. Re-running `scripts/01_fetch_osm.py` can fetch a different OSM state over time; metadata sidecars record query, timestamp, and file hash to make that visible.

## Seed Policy

Simulation outputs should retain per-seed metadata and reports should show successful seed counts. Presentation playback may use a representative seed, but the presentation manifest must declare which seed and selection policy were used.
