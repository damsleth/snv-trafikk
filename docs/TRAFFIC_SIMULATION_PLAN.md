# Snarøyveien Traffic Simulation Project

## Purpose

Build an open-source, AI-agent-friendly traffic microsimulation to demonstrate the congestion impact of narrowing Snarøyveien from today's 2+3 lane road to the proposed 2+2 "bygate" cross-section (KDP3 / Variant V1), with particular focus on the consequences for residents of the Snarøya peninsula.

The official traffic analysis (PGF, doc 7133122) already shows **~2 km queues** on Snarøyveien sør in morning rush and significant congestion at both roundabouts under Scenario 4A. This project aims to independently reproduce and extend those findings using open tools, making the results verifiable, adjustable, and presentable to decision-makers.

---

## Context: What Is Being Proposed

### The Road Today
- **Snarøyveien** (fv. 166) is the main arterial serving the Snarøya/Fornebu peninsula
- Between Rundkjøring Widerøeveien (north) and Rundkjøring Rolfsbuktveien (south): **2+3 lanes** (2 southbound + 3 northbound), ~1.2 km
- The stretch between Odd Nansens vei and Bernt Balchens vei is currently closed for Fornebubanen (Flytårnet station) construction
- All Snarøya traffic currently routes via Rolfsbuktveien loop

### The Proposal (Reguleringsplan, 2. gangs behandling 29.01.2026)
- Restablish Snarøyveien as a **"bygate"** with 2+2 kjørefelt (driving lanes)
- Add venstresvingefelt (left-turn lane) for southbound at Bernt Balchens vei
- Separate bike/pedestrian infrastructure on both sides
- Street trees, reduced speed (40 km/h), urban character
- **No dedicated kollektivfelt** until Fornebubanen is operational
- Midlertidig tiltak: busslommer (not kantstopp), no signed kollektivfelt northbound, central pedestrian crossing closed until metro opens

### Key Intersections (Capacity Bottlenecks)
1. **Nordre rundkjøring** (Snarøyveien x Widerøeveien) — 3-arm, connects to E18 via Vestre Lenke
2. **Lyskrysset** (Snarøyveien x Bernt Balchens vei) — signal-controlled, at Flytårnet station
3. **Søndre rundkjøring** (Snarøyveien x Rolfsbuktveien) — 3-arm, gateway to Snarøya/Hundsund

### The Core Problem
- Søndre rundkjøring has severe **skewed traffic distribution** in morning rush: the dominant northbound flow from Snarøyveien nord blocks entry from Snarøyveien sør
- The Aimsun analysis shows **309 vehicles queuing outside the model** on Snarøyveien sør in morning rush (Scenario 4A, V3)
- In afternoon rush, the signal at Bernt Balchens vei creates northbound backup because pedestrian phases interrupt vehicle throughput
- Capacity constraint is at the **roundabouts** (outside the plan area), not at the Flytårnet stretch itself

### Traffic Volumes (2040 projections, Scenario 4A peak hour)
| Location | Morning (veh/h) | Afternoon (veh/h) |
|---|---|---|
| Nordre rundkjøring total | 2,870 | 3,245 |
| Snarøyveien nord (into nordre) | 850 | 605 |
| Widerøeveien (into nordre) | 890 | 1,015 |
| Lyskrysset total | 2,310 | 2,520 |
| Søndre rundkjøring total | 2,150 | 2,240 |
| Snarøyveien sør (from Snarøya) | 650 | 535 |
| Rolfsbuktveien | 125 | 80 |

---

## Tech Stack

### Primary: SUMO (Simulation of Urban Mobility)
- **License**: EPL-2.0 (open source)
- **Why**: Industry-standard microsimulation, scriptable via Python (TraCI API), outputs detailed per-vehicle metrics, supports roundabouts, signal plans, lane restrictions, and O-D matrices
- **AI-friendly**: Full Python API, XML-based config (easy to generate/modify programmatically), CLI-driven (no GUI needed for batch runs)

### Supporting Tools
| Tool | Purpose | License |
|---|---|---|
| **SUMO** (sumo, netconvert, duarouter, od2trips) | Microsimulation engine | EPL-2.0 |
| **OSMWebWizard / osmGet** | Extract OpenStreetMap road network for Fornebu | EPL-2.0 (SUMO) |
| **netedit** | Visual network editing (optional, for manual tweaks) | EPL-2.0 |
| **Python 3.11+** | Orchestration, TraCI scripting, analysis | PSF |
| **pandas / matplotlib / plotly** | Data analysis and visualization | BSD |
| **sumolib** | Python helpers for SUMO network/route files | EPL-2.0 |
| **traci** | Live simulation control from Python | EPL-2.0 |
| **OpenStreetMap** | Base road network data | ODbL |
| **NVDB API** | Norwegian road database — lane counts, speed limits, AADT | Norsk lisens for offentlige data |
| **Jupyter Notebook** | Interactive exploration and presentation | BSD |

---

## Project Structure

```
SNV/
├── README.md
├── pyproject.toml                  # Python project config (uv/pip)
├── CLAUDE.md                       # AI agent instructions
│
├── docs/
│   ├── TRAFFIC_SIMULATION_PLAN.md  # This file (copy from SNV-DOCS)
│   └── reference/                  # Symlink or copy key PDFs from SNV-DOCS
│
├── network/
│   ├── osm/                        # Raw OSM extracts
│   │   └── fornebu.osm.xml
│   ├── base/                       # Current road network (today's lanes)
│   │   ├── fornebu.net.xml
│   │   ├── fornebu.edg.xml
│   │   └── fornebu.nod.xml
│   ├── proposed/                   # Modified network (2+2, KDP3 bygate)
│   │   ├── fornebu_v1.net.xml      # Variant V1 (recommended)
│   │   ├── fornebu_v2.net.xml      # Variant V2
│   │   └── fornebu_v3.net.xml      # Variant V3
│   └── signals/
│       └── bernt_balchens.add.xml  # Traffic light phases for lyskrysset
│
├── demand/
│   ├── od_matrices/                # Origin-Destination matrices
│   │   ├── morning_1A.csv          # Scenario 1A morning rush
│   │   ├── morning_4A.csv          # Scenario 4A morning rush
│   │   ├── afternoon_1A.csv
│   │   └── afternoon_4A.csv
│   ├── routes/
│   │   ├── morning_1A.rou.xml      # Generated vehicle routes
│   │   └── ...
│   └── taz/
│       └── fornebu.taz.xml         # Traffic Analysis Zones
│
├── scenarios/
│   ├── base_today/                 # Current situation (validation)
│   │   └── sumo.cfg
│   ├── scenario_1A_base/           # Sc. 1A with current lanes
│   │   └── sumo.cfg
│   ├── scenario_4A_base/           # Sc. 4A with current lanes
│   │   └── sumo.cfg
│   ├── scenario_4A_v1/             # Sc. 4A + Variant V1 (2+2, recommended)
│   │   └── sumo.cfg
│   ├── scenario_4A_v2/             # Sc. 4A + Variant V2
│   │   └── sumo.cfg
│   ├── scenario_4A_v3/             # Sc. 4A + Variant V3
│   │   └── sumo.cfg
│   └── scenario_4A_v1_mitigated/   # V1 + optimization measures
│       └── sumo.cfg
│
├── scripts/
│   ├── 01_fetch_osm.py             # Download OSM data for bounding box
│   ├── 02_build_network.py         # Convert OSM → SUMO net, apply edits
│   ├── 03_generate_demand.py       # OD matrices → vehicle routes
│   ├── 04_run_simulation.py        # Run one or all scenarios via TraCI
│   ├── 05_analyze_results.py       # Parse outputs, compute KPIs
│   ├── 06_generate_report.py       # Produce comparison charts/tables
│   └── utils/
│       ├── network_modifier.py     # Programmatic lane/speed changes
│       ├── signal_generator.py     # Generate .add.xml signal plans
│       └── nvdb_fetcher.py         # Pull AADT/speed data from NVDB API
│
├── notebooks/
│   ├── 01_exploration.ipynb        # Network inspection and validation
│   ├── 02_calibration.ipynb        # Tuning demand to match known counts
│   └── 03_results.ipynb            # Final comparison visualizations
│
├── output/                         # Simulation results (gitignored)
│   ├── scenario_4A_base/
│   ├── scenario_4A_v1/
│   └── ...
│
└── tests/
    ├── test_network.py             # Validate network topology
    └── test_demand.py              # Validate demand generation
```

---

## Implementation Plan

### Phase 1: Network Construction

**Goal**: Create an accurate SUMO road network for the Fornebu/Snarøya area.

#### 1.1 Extract OSM Base Network
- Bounding box: approximately `59.880,10.575` to `59.910,10.635` (Snarøya → E18)
- Use `osmGet.py` or Overpass API to download
- Convert with `netconvert --osm-files fornebu.osm.xml -o fornebu.net.xml`
- Include: Snarøyveien full length, Widerøeveien, Rolfsbuktveien, Odd Nansens vei, Bernt Balchens vei, Vestre Lenke, E18 on/off ramps

#### 1.2 Refine Network to Match Reality
- Verify lane counts against NVDB and aerial photos
- **Nordre rundkjøring**: 3-arm roundabout, 2 circulating lanes, approach lanes as per Aimsun model diagrams
- **Søndre rundkjøring**: 3-arm roundabout, verify approach geometry
- **Lyskrysset** (Bernt Balchens vei): signal-controlled, pedestrian phases
- Speed limits: 40 km/h on Snarøyveien (proposed), 60 km/h on connecting roads, verify via NVDB
- Correct any OSM errors in lane count, turn restrictions, junction types

#### 1.3 Create Variant Networks
- **Base (today)**: 2+3 lanes between roundabouts (as before Fornebubanen construction)
- **V1**: 2+2 kjørefelt + kantstopp for buss sørgående (A/B/C), 1 kjørefelt + 1 kollektivfelt m/kantstopp nordgående (C/B), 2 kjørefelt + 1 kollektivfelt nordgående (A)
- **V2**: 1 kjørefelt + 1 kollektivfelt sørgående (A/B/C), same as V1 northbound
- **V3**: Same as V1 southbound, 1 kjørefelt + 1 kollektivfelt nordgående from søndre rundkjøring to lyskrysset (C), 2 kjørefelt + 1 kollektivfelt on A
- Use `network_modifier.py` to programmatically adjust lane counts, allowed vehicle classes, and edge speeds

#### 1.4 Signal Plans
- Bernt Balchens vei signal: model phases based on traffic analysis figures
  - Northbound green phase
  - Southbound/eastbound green phase
  - Pedestrian phase (when central crossing is open)
- Parameterize cycle times so AI agents can test different timings

### Phase 2: Demand Modeling

**Goal**: Create realistic vehicle demand matching the PGF traffic analysis projections.

#### 2.1 Define Traffic Analysis Zones (TAZ)
- **Snarøya/Hundsund** (south of søndre rundkjøring)
- **Rolfsbuktveien** (east arm of søndre rundkjøring)
- **Snarøyveien øst** (Telenor/business district, east of lyskrysset)
- **Fornebu nord/Widerøeveien** (north/west via nordre rundkjøring)
- **E18 / Vestre Lenke** (external network, north via nordre rundkjøring)
- **Odd Nansens vei** (local access)
- **Bernt Balchens vei** (local access + Martin Linges vei connection)

#### 2.2 Build OD Matrices
- Source data: Figures 3-1 and 3-2 in Tilleggsnotatet (turning movement volumes per intersection for Scenario 4A, year 2040)
- Morning peak: 07:45–08:45
- Afternoon peak: 15:30–16:30
- Also build Scenario 1A matrices (higher volumes, 42,400 daily trips vs 31,300)
- Express as vehicles/hour per OD pair

**Key morning rush flows (Scenario 4A):**
| From → To | Veh/h |
|---|---|
| Snarøya → Nordre rundkjøring (via søndre) | ~650 |
| Snarøya → Snarøyveien øst | ~35 |
| Rolfsbuktveien → Nord | ~125 |
| Widerøeveien → Snarøyveien sør | ~310 |
| Snarøyveien nord → Widerøeveien | ~365 |
| Snarøyveien nord → Snarøyveien (southbound) | ~850 |

#### 2.3 Generate Routes
- Use `od2trips` + `duarouter` to convert OD matrices to individual vehicle routes
- Apply departure time distribution within the peak hour (e.g., Poisson or empirical)
- Calibrate so simulated intersection counts match the PGF figures

### Phase 3: Simulation Execution

**Goal**: Run all scenarios and collect output data.

#### 3.1 Scenario Matrix

| Scenario | Network | Demand | Description |
|---|---|---|---|
| `base_today` | Current (2+3) | Estimated current | Validation against known conditions |
| `scenario_1A_base` | Current (2+3) | Sc. 1A (42,400/day) | What if we kept today's lanes with full buildout? |
| `scenario_4A_base` | Current (2+3) | Sc. 4A (31,300/day) | Baseline comparison |
| `scenario_4A_v1` | V1 (2+2) | Sc. 4A | **Main scenario: the proposed plan** |
| `scenario_4A_v2` | V2 (1+1+kollektiv) | Sc. 4A | Worst-case variant |
| `scenario_4A_v3` | V3 (hybrid) | Sc. 4A | Interim variant |
| `scenario_1A_v1` | V1 (2+2) | Sc. 1A | Worst-case demand + proposed lanes |
| `scenario_4A_v1_opt` | V1 + optimizations | Sc. 4A | With tilfartsregulering, signal tuning etc. |

#### 3.2 Simulation Parameters
- Simulation period: 2 hours (1h warm-up + 1h peak measurement), or 90 min peak window
- Step length: 1 second
- Car-following model: Krauss (SUMO default) — good for congestion modeling
- Lane-change model: SL2015 (realistic lane-change behavior)
- Random seed: Run each scenario 5x with different seeds for statistical robustness

#### 3.3 TraCI Data Collection
Collect per-simulation-step via TraCI or SUMO outputs:
- **Edge travel times** (per road segment)
- **Queue lengths** at roundabout approaches and signal stop lines
- **Vehicle counts** per edge per time interval
- **Delay** (actual travel time minus free-flow travel time)
- **Vehicles waiting** (speed < 0.1 m/s)
- Number of vehicles that **cannot enter the network** (teleported / waiting to depart)

### Phase 4: Analysis and KPIs

**Goal**: Compute and compare metrics that quantify the impact on Snarøya residents.

#### 4.1 Key Performance Indicators

| KPI | Unit | Why It Matters |
|---|---|---|
| **Queue length on Snarøyveien sør** | meters / vehicles | Direct measure of blockage for Snarøya residents |
| **Travel time Snarøya → E18** | seconds | Door-to-highway commute time |
| **Travel time Snarøya → Bernt Balchens vei** | seconds | Access to Flytårnet station (future metro) |
| **Average delay per vehicle** | seconds | Overall network performance |
| **Max queue at søndre rundkjøring** | vehicles | Risk of spillback onto Snarøya residential streets |
| **Throughput nordre rundkjøring** | veh/h | Bottleneck capacity utilization |
| **Time spent in queue** | veh-hours | Aggregate congestion cost |
| **CO₂ proxy** (total veh-km × idle time) | kg estimate | Environmental argument |

#### 4.2 Comparison Outputs
- Bar charts: KPI comparison across all scenarios
- Time-series: Queue length evolution over the rush hour
- Heatmaps: Network delay visualization (which links are worst)
- Animation: SUMO-GUI replay of worst-case scenario (for presentations)

### Phase 5: Report Generation

**Goal**: Produce a clear, evidence-based report suitable for submission to Bærum kommune.

#### 5.1 Report Structure
1. **Executive Summary** — Key finding: the proposed 2+2 configuration creates X minutes additional delay and Y km queues for Snarøya residents compared to maintaining current capacity
2. **Methodology** — Open, reproducible, based on same traffic volumes as official analysis
3. **Scenario Comparison** — Side-by-side results with charts
4. **Sensitivity Analysis** — What if demand is 10-20% higher/lower than projected?
5. **Critique of Assumptions** — The official analysis assumes Fornebubanen + Vestre Lenke will reduce traffic; what if they don't? What about construction period?
6. **Recommendations** — Specific capacity-preserving alternatives
7. **Appendix** — Full data tables, methodology details, how to reproduce

#### 5.2 Key Arguments to Quantify
- The **2 km queue** finding from PGF's own analysis is already alarming — our simulation should corroborate or exceed this
- Scenario 1A (higher parking norm = more cars) is more realistic than 4A given actual development trends
- The **midlertidige tiltak** (no kollektivfelt, busslommer instead of kantstopp) may persist for years before Fornebubanen opens (~2028+)
- Emergency vehicle access to Snarøya/Langodden is compromised during peak congestion
- The capacity bottleneck is at the **roundabouts**, which are **outside the plan area** and not being improved

---

## Getting Started

### Prerequisites
```bash
# Install SUMO (macOS)
brew install sumo

# Or via conda
conda install -c conda-forge sumo

# Verify
sumo --version

# Python environment
uv init
uv add sumolib traci pandas matplotlib plotly jupyter lxml requests
```

### Environment Variables
```bash
export SUMO_HOME=$(brew --prefix sumo)/share/sumo  # macOS
# or: export SUMO_HOME=/usr/share/sumo             # Linux
```

### Quick Start
```bash
# 1. Fetch OSM data for Fornebu area
python scripts/01_fetch_osm.py

# 2. Build SUMO network (base + variants)
python scripts/02_build_network.py

# 3. Generate traffic demand from OD matrices
python scripts/03_generate_demand.py

# 4. Run all scenarios
python scripts/04_run_simulation.py --all

# 5. Analyze and compare
python scripts/05_analyze_results.py

# 6. Generate report
python scripts/06_generate_report.py
```

---

## CLAUDE.md Guidance for AI Agents

The project should include a `CLAUDE.md` with these instructions:

```
# Snarøyveien Traffic Simulation

## What This Is
SUMO microsimulation comparing traffic impacts of narrowing Snarøyveien
from 2+3 to 2+2 lanes (KDP3 bygate proposal) on Snarøya peninsula residents.

## Key Files
- network/ — SUMO road networks (base and variants)
- demand/ — OD matrices and generated vehicle routes
- scenarios/ — Runnable SUMO configurations
- scripts/ — Python pipeline (numbered 01-06, run in order)
- notebooks/ — Jupyter analysis notebooks

## How to Run
1. `python scripts/01_fetch_osm.py` — downloads OSM data
2. `python scripts/02_build_network.py` — builds all network variants
3. `python scripts/03_generate_demand.py` — creates vehicle routes
4. `python scripts/04_run_simulation.py --scenario scenario_4A_v1` — run one
5. `python scripts/05_analyze_results.py` — compute KPIs

## Conventions
- All traffic volumes from PGF traffic analysis (doc 7133122) and
  Multiconsult Trafikkanalyse Fornebu KDP3 (2022)
- Scenario 4A = full buildout 2040, tightened parking norm (31,300 trips/day)
- Scenario 1A = full buildout 2040, current parking norm (42,400 trips/day)
- Variants V1/V2/V3 = different lane configurations per PGF analysis
- Peak hours: morning 07:45-08:45, afternoon 15:30-16:30
- Network modifications should be done via scripts, not manual netedit edits
- Run each scenario with 5 random seeds for statistical validity

## Important Context
- Snarøya is a peninsula — there is only ONE road in/out (Snarøyveien)
- The capacity bottleneck is at the roundabouts, not the Flytårnet stretch
- Søndre rundkjøring has severe skewed distribution in morning rush
- The official analysis already shows ~2 km queues and 309 vehicles
  stuck outside the model in morning rush
- Residents and local politicians are concerned about emergency access
```

---

## Data Sources

| Source | What | How to Get |
|---|---|---|
| OpenStreetMap | Road geometry, lanes, speed limits | Overpass API / osmGet.py |
| NVDB (vegkart.atlas.vegvesen.no) | Official lane counts, AADT, speed limits | REST API (free) |
| PGF Trafikkanalyse (doc 7133122) | Turning movement volumes, model results | PDF in SNV-DOCS/ |
| PGF Tilleggsnotat (doc 7133121) | Optimization measures, additional analysis | PDF in SNV-DOCS/ |
| Multiconsult KDP3 (doc 7141178) | Regional traffic volumes, scenarios | PDF in SNV-DOCS/ |
| Reguleringsplan 2. gangs beh. | Current political decisions, plan details | PDF in SNV-DOCS/ |

---

## Risk and Limitations

- **Model simplification**: SUMO microsimulation with an OD-matrix-driven demand is simpler than the Aimsun model used by PGF, but sufficient for comparative analysis (same demand, different network = fair comparison)
- **Roundabout calibration**: SUMO's roundabout behavior may differ from Aimsun. Calibrate gap acceptance parameters against known capacity (~3,500 veh/h for 3-arm roundabout per PGF rule-of-thumb)
- **No public transit modeling**: Buses are not explicitly modeled in the initial version. Can be added in Phase 2 if needed (SUMO supports bus routes and stops)
- **Static OD demand**: Real demand is elastic (people change routes/modes when congestion increases). Our model uses fixed demand, which is conservative — it shows what happens if people *don't* change behavior, which is the realistic short-term response
- **Not a replacement for professional analysis**: This is a citizen-produced independent verification using the same input data as the official analysis. It should complement, not claim to supersede, the professional work

---

## Timeline Estimate

| Phase | Effort |
|---|---|
| Phase 1: Network | Build OSM extraction, verify/fix lanes and junctions |
| Phase 2: Demand | Encode OD matrices from PGF figures, calibrate routes |
| Phase 3: Simulation | Run all scenarios (automated, fast once set up) |
| Phase 4: Analysis | Compute KPIs, generate visualizations |
| Phase 5: Report | Write up findings for kommune submission |

Each phase is designed to be independently verifiable and modifiable by AI agents. The numbered scripts provide a clear pipeline from raw data to final report.
