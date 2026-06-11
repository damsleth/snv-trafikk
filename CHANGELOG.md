# Changelog

All notable public-facing changes to `snv-trafikk` are tracked here. For detailed working notes, see [docs/DEVLOG.md](docs/DEVLOG.md).

## Unreleased

### Added

- Scenario catalog validation via `scripts/00_validate_setup.py`.
- Simulation output integrity metadata, strict XML handling, retry-failed support, and generated config hygiene flags in `scripts/04_run_simulation.py`.
- OSM, demand, and simulation provenance sidecars for more auditable reruns.
- Catalog-driven presentation exports with explicit seed policy and manifest provenance.
- Lightweight validation report generation in analysis and validation warnings in the generated report.
- Python CI quality workflow plus pytest, ruff, and mypy configuration.
- Frontend Vitest harness for presentation data-loading logic.
- Presentation loading resilience, safer DOM rendering paths, server request hardening, and improved responsive/accessibility affordances.
- Documentation for development, scenario assumptions, and DATEX2/trafikkdata refresh work.

### Changed

- Scenario families now carry status/export metadata so main, reference, sensitivity, and exploratory scenarios are easier to distinguish.
- The local presentation server now sends security headers and validates patched-run payloads.

### Notes

- `.plans/` remains local uncommitted working state by policy.
- External/manual tasks such as GitHub Pages settings and live Trafikkdata API pulls are documented but not performed automatically.
