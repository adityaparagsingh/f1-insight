"""F1 INSIGHT ETL command line.

Examples
--------
    python -m etl.run --season 2024
    python -m etl.run --all
    python -m etl.run --update
    python -m etl.run --all --stage reference,results
    python -m etl.run --season 1998 --stage standings --skip-laps
"""
from __future__ import annotations

import argparse
import json
import sys

from etl.logging_utils import get_logger
from etl.runner import ALL_STAGES, EtlRunner

log = get_logger("etl.cli")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m etl.run",
        description="F1 INSIGHT: extract Jolpica F1 data into the MySQL star schema.",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--season", type=int, metavar="YYYY",
                      help="Load one season end-to-end")
    mode.add_argument("--all", action="store_true",
                      help="Load the full historical warehouse (default scope)")
    mode.add_argument("--update", action="store_true",
                      help="Incrementally load only missing rounds of the latest season")

    p.add_argument("--stage", metavar="LIST",
                   help=f"Comma-separated subset of stages: {','.join(ALL_STAGES)}")
    p.add_argument("--lap-start", type=int, default=2015,
                   help="Earliest season with lap-time extraction in --all (default 2015)")
    p.add_argument("--pit-start", type=int, default=2011,
                   help="Earliest season with pit-stop extraction in --all (default 2011)")
    p.add_argument("--standings-since", type=int, default=1980,
                   help="Earliest season with per-round standings in --all (default 1980)")
    p.add_argument("--skip-laps", action="store_true", help="Skip the lap-time stage")
    p.add_argument("--skip-pitstops", action="store_true", help="Skip the pit-stop stage")
    p.add_argument("--skip-standings", action="store_true", help="Skip the standings stage")
    p.add_argument("--no-cache", action="store_true", help="Disable the raw-response disk cache")
    p.add_argument("--refresh-cache", action="store_true", help="Ignore cached responses")
    p.add_argument("--rps", type=float, default=None,
                   help="Max API requests per second (overrides env)")
    p.add_argument("--retries", type=int, default=None, help="Max retries per request")
    p.add_argument("--json", action="store_true", help="Print final summary as JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.season is not None:
        mode = "season"
        season = args.season
    elif args.all:
        mode = "all"
        season = None
    elif args.update:
        mode = "update"
        season = None
    else:
        mode = "update"  # safe default: incremental
        season = None

    stages = None
    if args.stage:
        stages = tuple(s.strip() for s in args.stage.split(",") if s.strip())
    excluded = set()
    if args.skip_laps:
        excluded.add("laps")
    if args.skip_pitstops:
        excluded.add("pitstops")
    if args.skip_standings:
        excluded.add("standings")
    if stages:
        stages = tuple(s for s in stages if s not in excluded)
    elif excluded:
        stages = tuple(s for s in ALL_STAGES if s not in excluded)

    runner = EtlRunner(
        lap_start=args.lap_start,
        pit_start=args.pit_start,
        standings_since=args.standings_since,
        use_cache=not args.no_cache,
        refresh_cache=args.refresh_cache,
        requests_per_second=args.rps,
        max_retries=args.retries,
    )
    try:
        summary = runner.run(mode, season=season, stages=stages)
    except KeyboardInterrupt:  # pragma: no cover
        log.error("interrupted by user")
        return 130
    except Exception as exc:
        log.exception("ETL failed: %s", exc)
        return 1
    finally:
        runner.close()

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print("\n================ F1 INSIGHT ETL SUMMARY ================")
        for k, v in summary.items():
            if k in ("etl_stats", "client_stats"):
                continue
            print(f"  {k:<26} {v:,}" if isinstance(v, int) else f"  {k:<26} {v}")
        print("  ---- data quality ----")
        for k, v in summary["etl_stats"].items():
            if k != "issues":
                print(f"  {k:<26} {v}")
        print("  ---- api client ----")
        for k, v in summary["client_stats"].items():
            print(f"  {k:<26} {v:,}")
        if summary["etl_stats"]["issues"]:
            print("  ---- sample issues (max 50 collected) ----")
            for issue in summary["etl_stats"]["issues"][:15]:
                print(f"   * {issue}")
        print("========================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
