# Snarøyveien Traffic Simulation

## What This Is
SUMO microsimulation comparing traffic impacts of narrowing Snarøyveien
from 2+3 to 2+2 lanes (KDP3 bygate proposal) on Snarøya peninsula residents.

## Key Files
- network/ — SUMO road networks (base and variants)
- demand/ — OD matrices and generated vehicle routes
- scenarios/ — Runnable SUMO configurations
- scripts/ — Python pipeline (numbered 01-06, run in order)

## How to Run
```bash
uv run python scripts/01_fetch_osm.py
uv run python scripts/02_build_network.py
uv run python scripts/03_generate_demand.py
uv run python scripts/04_run_simulation.py --all
uv run python scripts/05_analyze_results.py
uv run python scripts/06_generate_report.py
```

## Conventions
- All traffic volumes from PGF traffic analysis (doc 7133122) and
  Multiconsult Trafikkanalyse Fornebu KDP3 (2022)
- Scenario 4A = full buildout 2040, tightened parking norm (31,300 trips/day)
- Scenario 1A = full buildout 2040, current parking norm (42,400 trips/day)
- Variants V1/V2/V3 = different lane configurations per PGF analysis
- Peak hours: morning 07:45-08:45, afternoon 15:30-16:30
- Network modifications done via scripts, not manual netedit edits
- Run each scenario with 5 random seeds for statistical validity
- Use `uv run` to execute all Python scripts

## Important Context
- Snarøya is a peninsula — there is only ONE road in/out (Snarøyveien)
- The capacity bottleneck is at the roundabouts, not the Flytårnet stretch
- Søndre rundkjøring has severe skewed distribution in morning rush
- The official analysis already shows ~2 km queues and 309 vehicles
  stuck outside the model in morning rush
- Residents and local politicians are concerned about emergency access

## SUMO_HOME
Set automatically by eclipse-sumo pip package. The tools (netconvert, duarouter, etc.)
are available via `uv run netconvert`, `uv run duarouter`, etc.

## Code conventions
- Python scripts use type hints and docstrings
- SUMO network modifications are preferrably done via Python scripts, not manual netedit
- Data files are in CSV/JSON/GeoJSON for easy analysis and visualization
- Results are stored in `output/` with scenario-specific subfolders
- JavaScript code in `web/presentation/app.js` uses modular functions and event listeners for interactivity
- JavaScript does not have any unnecessary semicolons.

## Devlog and planning conventions
- Always keep `docs/DEVLOG.md` up to date as work progresses; add new entries reverse chronologically with date, timestamp, and a short description of the change before finishing work.
- Keep `.plans/` as local, uncommitted working state. Do not stage or commit files from `.plans/`.
- Keep active todos and plans in `.plans/TODO.md`, updating them as work progresses.
- When work is finished, move completed todos and plan notes from `.plans/TODO.md` to `.plans/DONE.md`, and move finished plan documents into `.plans/done/`.

### Code Intelligence

Prefer LSP over Grep/Glob/Read for code navigation:
- `goToDefinition` / `goToImplementation` to jump to source
- `findReferences` to see all usages across the codebase
- `workspaceSymbol` to find where something is defined
- `documentSymbol` to list all symbols in a file
- `hover` for type info without reading the file
- `incomingCalls` / `outgoingCalls` for call hierarchy

Before renaming or changing a function signature, use
`findReferences` to find all call sites first.

Use Grep/Glob only for text/pattern searches (comments,
strings, config values) where LSP doesn't help.

After writing or editing code, check LSP diagnostics before
moving on. Fix any type errors or missing imports immediately.