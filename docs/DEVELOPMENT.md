# Development

This repository uses `uv` for Python dependency management and keeps generated/local working state out of git where possible.

## Local Quality Checks

Run the fast Python checks before larger changes:

```bash
uv run --extra dev pytest -q
uv run python -m compileall scripts tests
uv run ruff check .
uv run mypy scripts tests
```

Mypy is currently configured as a non-blocking baseline while the older dynamic script dictionaries are typed incrementally. Tightening it should be done in small follow-up changes so type cleanup does not obscure traffic-model changes.

The default pytest path excludes tests marked `slow` or `sumo` in CI. SUMO-dependent smoke tests should be marked explicitly so pull-request checks stay quick.

## Presentation Tests

The web presentation has isolated Node tooling under `web/presentation/`.

```bash
cd web/presentation
npm install
npm test
```

Use small fixtures in web tests; do not require full-size `web/presentation/data/playback/*.json` in CI.

## Setup Validation

Use the setup validator before rerunning the full pipeline:

```bash
uv run python scripts/00_validate_setup.py
```

It checks scenario catalog shape, required input files, export eligibility, and local orphaned scenario/output folders.

## Generated Config Hygiene

SUMO config files under `scenarios/**/sumo_seed*.cfg` are generated local working files and must stay uncommitted.

```bash
uv run python scripts/04_run_simulation.py --clean-configs --dry-run
uv run python scripts/04_run_simulation.py --generate-configs-only --scenario scenario_4A_base_morning --seeds 5
```

The runner validates generated configs for stale absolute local paths.

## Provenance

Pipeline scripts now write lightweight metadata sidecars for OSM, demand, and simulation outputs where relevant. These files are meant to make reruns auditable and to support later calibration checks.
