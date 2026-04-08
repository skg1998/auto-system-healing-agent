from __future__ import annotations

import argparse
import importlib.metadata
import logging
from pathlib import Path

from self_healing_agent.adapters.select import build_psutil_adapter
from self_healing_agent.application.pipeline import Pipeline
from self_healing_agent.application.runner import load_app_config, run_forever
from self_healing_agent.core.buffer import TickBuffer


def _package_version() -> str:
    try:
        return importlib.metadata.version("self-healing-agent")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def _print_tick_summary(pipeline: Pipeline) -> None:
    rec = pipeline.tick()
    s = rec.snapshot
    logging.info(
        "cpu=%.1f%% mem=%s/%s MB swap=%s MB disk_r=%s disk_w=%s net↑=%s net↓=%s",
        s.cpu_total_pct,
        round(s.mem_used_bytes / 1_000_000, 1),
        round(s.mem_total_bytes / 1_000_000, 1),
        round((s.swap_used_bytes or 0) / 1_000_000, 1),
        f"{s.disk_read_bps:.0f}" if s.disk_read_bps is not None else "n/a",
        f"{s.disk_write_bps:.0f}" if s.disk_write_bps is not None else "n/a",
        f"{s.net_sent_bps:.0f}" if s.net_sent_bps is not None else "n/a",
        f"{s.net_recv_bps:.0f}" if s.net_recv_bps is not None else "n/a",
    )
    for p in rec.processes[:5]:
        logging.info(
            "  pid=%s cpu=%.1f%% rss=%sMB name=%s",
            p.pid,
            p.cpu_pct,
            round(p.rss_bytes / 1_000_000, 1),
            p.name,
        )


def cmd_once(verbose: bool) -> int:
    _setup_logging(verbose)
    adapter = build_psutil_adapter()
    buf = TickBuffer()
    pipeline = Pipeline(adapter, adapter, buf)
    _print_tick_summary(pipeline)
    return 0


def cmd_run(
    interval: float | None,
    config_path: Path | None,
    dry_run: bool,
    quiet: bool,
    verbose: bool,
) -> int:
    _setup_logging(verbose)
    cfg = load_app_config(config_path)
    if interval is not None:
        cfg.agent.tick_interval_seconds = interval
    run_forever(cfg, dry_run=dry_run, quiet=quiet)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sha-agent", description="Local observability agent")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("once", help="Single collect + print summary")

    p_run = sub.add_parser("run", help="Loop: collect, detect sustained load, notify (log)")
    p_run.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Override config agent.tick_interval_seconds",
    )
    p_run.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML config file (defaults: built-in defaults if omitted)",
    )
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be notified without treating as a real alert",
    )
    p_run.add_argument(
        "--quiet",
        action="store_true",
        help="Less per-tick output (detection still runs)",
    )

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    if args.command == "once":
        return cmd_once(args.verbose)
    if args.command == "run":
        return cmd_run(
            interval=args.interval,
            config_path=args.config,
            dry_run=args.dry_run,
            quiet=args.quiet,
            verbose=args.verbose,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
