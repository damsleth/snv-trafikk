#!/usr/bin/env python3
"""Validate local setup before running the SNV traffic pipeline."""

from __future__ import annotations

import argparse
import json
import sys

from utils.scenario_catalog import validate_scenario_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate scenario catalog and local input files")
    parser.add_argument("--no-file-check", action="store_true", help="Skip network/route/additional file existence checks")
    parser.add_argument("--no-orphans", action="store_true", help="Skip local orphaned scenario/output folder warnings")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    report = validate_scenario_catalog(
        check_files=not args.no_file_check,
        check_orphans=not args.no_orphans,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("SNV setup validation")
        print(f"  scenarios: {report['scenario_count']}")
        print(f"  presentation exports: {report['export_count']}")
        for warning in report["warnings"]:
            print(f"  WARNING: {warning}")
        for error in report["errors"]:
            print(f"  ERROR: {error}")
        print("  status: OK" if report["valid"] else "  status: FAILED")

    if not report["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
