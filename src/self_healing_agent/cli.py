from __future__ import annotations

import argparse
import logging
import sys
import time

from self_healing_agent.adapters.psutil_adapter import PsutilAdapter
from self_healing_agent.application.pipeline import Pipeline
from self_healing_agent.core.buffer import TickBuffer


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
    top = rec.processes[:5]
    for p in top:
        logging.info(
            "  pid=%s cpu=%.1f%% rss=%sMB name=%s",
            p.pid,
            p.cpu_pct,
            round(p.rss_bytes / 1_000_000, 1),
            p.name,
        )


def cmd_once(verbose: bool) -> int:
    _setup_logging(verbose)
    adapter = PsutilAdapter()
    buf = TickBuffer()
    pipeline = Pipeline(adapter, adapter, buf)
    _print_tick_summary(pipeline)
    return 0


def cmd_run(interval: float, verbose: bool) -> int:
    _setup_logging(verbose)
    adapter = PsutilAdapter()
    buf = TickBuffer()
    pipeline = Pipeline(adapter, adapter, buf)
    logging.info("Running every %ss — Ctrl+C to stop", interval)
    try:
        while True:
            _print_tick_summary(pipeline)
            time.sleep(max(0.5, interval))
    except KeyboardInterrupt:
        logging.info("Stopped.")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sha-agent", description="Local observability agent")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("once", help="Single collect + print summary")

    p_run = sub.add_parser("run", help="Loop collect + print summary")
    p_run.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds between ticks (default 5)",
    )

    args = parser.parse_args(argv)
    if args.command == "once":
        return cmd_once(args.verbose)
    if args.command == "run":
        return cmd_run(args.interval, args.verbose)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
