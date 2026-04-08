from __future__ import annotations

import logging
import time
from pathlib import Path

from self_healing_agent.adapters.logging_notifier import LoggingNotifier
from self_healing_agent.adapters.psutil_actions import PsutilActionExecutor
from self_healing_agent.adapters.select import build_psutil_adapter
from self_healing_agent.application.pipeline import Pipeline
from self_healing_agent.config.load import default_config, load_config
from self_healing_agent.config.models import AppConfig
from self_healing_agent.core.buffer import TickBuffer
from self_healing_agent.core.detection import DetectionEngine
from self_healing_agent.core.diagnosis import DiagnosisEngine
from self_healing_agent.core.policy import (
    HardTerminateIntent,
    NotifyDiagnosisIntent,
    NotifySignalsIntent,
    PolicyEngine,
    SoftReniceIntent,
    SuggestIntent,
)

log = logging.getLogger(__name__)


def load_app_config(config_path: Path | None) -> AppConfig:
    if config_path is None:
        return default_config()
    return load_config(config_path)


def run_forever(
    cfg: AppConfig,
    *,
    dry_run: bool,
    quiet: bool = False,
) -> None:
    """Collect metrics on an interval, detect sustained conditions, notify."""
    buf = TickBuffer(maxlen=cfg.agent.buffer_max_ticks)
    adapter = build_psutil_adapter()
    pipeline = Pipeline(adapter, adapter, buf)
    detector = DetectionEngine(cfg.detection)
    diagnoser = DiagnosisEngine(cfg.diagnosis)
    policy_engine = PolicyEngine(cfg.policy)
    executor = PsutilActionExecutor()
    notifier = LoggingNotifier(dry_run=dry_run)

    interval = cfg.agent.tick_interval_seconds
    log.info(
        "Agent loop: interval=%ss buffer_max=%s detection=%s diagnosis=%s "
        "policy=%s soft=%s hard_kill=%s dry_run=%s",
        interval,
        cfg.agent.buffer_max_ticks,
        cfg.detection.enabled,
        cfg.diagnosis.enabled,
        cfg.policy.enabled,
        cfg.policy.soft_actions_enabled,
        cfg.policy.hard_kill_enabled,
        dry_run,
    )

    try:
        while True:
            _tick_once(
                cfg,
                pipeline,
                buf,
                detector,
                diagnoser,
                policy_engine,
                executor,
                notifier,
                dry_run=dry_run,
                quiet=quiet,
            )
            time.sleep(max(0.5, interval))
    except KeyboardInterrupt:
        log.info("Stopped.")


def _tick_once(
    cfg: AppConfig,
    pipeline: Pipeline,
    buffer: TickBuffer,
    detector: DetectionEngine,
    diagnoser: DiagnosisEngine,
    policy_engine: PolicyEngine,
    executor: PsutilActionExecutor,
    notifier: LoggingNotifier,
    *,
    dry_run: bool,
    quiet: bool,
) -> None:
    rec = pipeline.tick()
    if not quiet:
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

    signals = detector.evaluate(buffer)
    hyps = diagnoser.diagnose(buffer, signals) if cfg.diagnosis.enabled and signals else []
    actions = policy_engine.decide(
        signals=signals,
        hypotheses=hyps,
        latest=rec,
    )
    for act in actions:
        if isinstance(act, NotifySignalsIntent):
            for s in act.signals:
                notifier.notify(s)
        elif isinstance(act, NotifyDiagnosisIntent):
            notifier.notify_diagnosis(act.hypotheses)
        elif isinstance(act, SuggestIntent):
            log.info("suggestion: %s", act.text)
        elif isinstance(act, SoftReniceIntent):
            executor.soft_renice(act, dry_run=dry_run)
        elif isinstance(act, HardTerminateIntent):
            ok = executor.hard_terminate(act, dry_run=dry_run)
            if ok and not dry_run:
                policy_engine.record_hard_kill_executed()
