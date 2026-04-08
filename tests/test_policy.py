from self_healing_agent.config.models import PolicySettings
from self_healing_agent.core.buffer import TickRecord
from self_healing_agent.core.detection import DetectionSignal
from self_healing_agent.core.diagnosis import DiagnosisHypothesis, EvidenceRef
from self_healing_agent.core.models import ProcessSample, SnapshotCapabilities, SystemSnapshot
from self_healing_agent.core.policy import (
    HardTerminateIntent,
    PolicyEngine,
    SoftReniceIntent,
    SuggestIntent,
)


def _snap(cpu: float = 50.0) -> SystemSnapshot:
    total = 10_000_000_000
    return SystemSnapshot(
        timestamp_monotonic_s=0.0,
        cpu_total_pct=cpu,
        mem_used_bytes=total // 2,
        mem_total_bytes=total,
        swap_used_bytes=0,
        disk_read_bps=0.0,
        disk_write_bps=0.0,
        net_sent_bps=0.0,
        net_recv_bps=0.0,
        thermal_c=None,
        capabilities=SnapshotCapabilities(),
    )


def _proc(pid: int, name: str, cpu: float) -> ProcessSample:
    return ProcessSample(
        pid=pid,
        parent_pid=None,
        name=name,
        cpu_pct=cpu,
        rss_bytes=100_000_000,
        thread_count=None,
    )


def _cpu_hypothesis(hid: str, conf: float) -> DiagnosisHypothesis:
    return DiagnosisHypothesis(
        hypothesis_id=hid,
        summary="s",
        confidence=conf,
        evidence=(EvidenceRef("e", "x"),),
    )


def test_policy_emits_notifications_only_when_enabled_off_soft_hard():
    pol = PolicyEngine(
        PolicySettings(
            enabled=False,
            soft_actions_enabled=True,
            hard_kill_enabled=True,
        )
    )
    sigs = (DetectionSignal(kind="high_system_cpu", message="m"),)
    hyps = (_cpu_hypothesis("cpu_compute_bound", 0.9),)
    rec = TickRecord(_snap(), (_proc(99, "app", 50.0),))
    acts = pol.decide(signals=sigs, hypotheses=hyps, latest=rec)
    kinds = [type(a).__name__ for a in acts]
    assert kinds == ["NotifySignalsIntent", "NotifyDiagnosisIntent"]


def test_suggestions_when_hypotheses_present():
    pol = PolicyEngine(PolicySettings(suggestions_enabled=True))
    sigs: tuple[DetectionSignal, ...] = ()
    hyps = (_cpu_hypothesis("cpu_compute_bound", 0.5),)
    acts = pol.decide(signals=sigs, hypotheses=hyps, latest=None)
    assert any(isinstance(a, SuggestIntent) for a in acts)


def test_soft_renice_when_gates_pass():
    pol = PolicyEngine(
        PolicySettings(
            soft_actions_enabled=True,
            min_confidence_for_soft=0.4,
            min_cpu_share_for_soft=5.0,
        )
    )
    sigs = (DetectionSignal(kind="high_system_cpu", message="m"),)
    hyps = (_cpu_hypothesis("cpu_compute_bound", 0.5),)
    rec = TickRecord(_snap(), (_proc(4242, "myapp", 20.0),))
    acts = pol.decide(signals=sigs, hypotheses=hyps, latest=rec)
    soft = [a for a in acts if isinstance(a, SoftReniceIntent)]
    assert len(soft) == 1
    assert soft[0].pid == 4242


def test_soft_skips_protected_name():
    pol = PolicyEngine(
        PolicySettings(
            soft_actions_enabled=True,
            min_confidence_for_soft=0.4,
            min_cpu_share_for_soft=5.0,
            protected_process_names=["svchost"],
        )
    )
    sigs = (DetectionSignal(kind="high_system_cpu", message="m"),)
    hyps = (_cpu_hypothesis("cpu_compute_bound", 0.5),)
    rec = TickRecord(_snap(), (_proc(12, "svchost", 90.0),))
    acts = pol.decide(signals=sigs, hypotheses=hyps, latest=rec)
    assert not any(isinstance(a, SoftReniceIntent) for a in acts)


def test_hard_kill_blocked_by_soft_taking_precedence():
    pol = PolicyEngine(
        PolicySettings(
            soft_actions_enabled=True,
            hard_kill_enabled=True,
            min_confidence_for_soft=0.4,
            min_confidence_for_hard=0.5,
            min_cpu_share_for_soft=5.0,
            min_cpu_share_for_hard=5.0,
        )
    )
    sigs = (DetectionSignal(kind="high_system_cpu", message="m"),)
    hyps = (_cpu_hypothesis("cpu_compute_bound", 0.7),)
    rec = TickRecord(_snap(), (_proc(9000, "app", 40.0),))
    acts = pol.decide(signals=sigs, hypotheses=hyps, latest=rec)
    assert any(isinstance(a, SoftReniceIntent) for a in acts)
    assert not any(isinstance(a, HardTerminateIntent) for a in acts)


def test_hard_kill_cooldown():
    pol = PolicyEngine(
        PolicySettings(
            hard_kill_enabled=True,
            min_confidence_for_hard=0.5,
            min_cpu_share_for_hard=5.0,
            hard_kill_max_per_window=1,
            hard_kill_cooldown_seconds=3600,
        )
    )
    sigs: tuple[DetectionSignal, ...] = ()
    hyps = (_cpu_hypothesis("cpu_compute_bound", 0.7),)
    rec = TickRecord(_snap(), (_proc(8000, "app", 40.0),))
    t0 = 1000.0
    a1 = pol.decide(signals=sigs, hypotheses=hyps, latest=rec, monotonic_now=t0)
    assert any(isinstance(a, HardTerminateIntent) for a in a1)
    pol.record_hard_kill_executed(monotonic_now=t0)
    a2 = pol.decide(signals=sigs, hypotheses=hyps, latest=rec, monotonic_now=t0 + 10.0)
    assert not any(isinstance(a, HardTerminateIntent) for a in a2)


def test_hard_allowed_after_window():
    pol = PolicyEngine(
        PolicySettings(
            hard_kill_enabled=True,
            min_confidence_for_hard=0.5,
            min_cpu_share_for_hard=5.0,
            hard_kill_max_per_window=1,
            hard_kill_cooldown_seconds=60,
        )
    )
    sigs: tuple[DetectionSignal, ...] = ()
    hyps = (_cpu_hypothesis("cpu_compute_bound", 0.7),)
    rec = TickRecord(_snap(), (_proc(8000, "app", 40.0),))
    t0 = 1000.0
    pol.record_hard_kill_executed(monotonic_now=t0)
    a2 = pol.decide(signals=sigs, hypotheses=hyps, latest=rec, monotonic_now=t0 + 61.0)
    assert any(isinstance(a, HardTerminateIntent) for a in a2)
