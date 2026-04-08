from self_healing_agent.config.models import DetectionSettings
from self_healing_agent.core.buffer import TickBuffer, TickRecord
from self_healing_agent.core.detection import DetectionEngine
from self_healing_agent.core.models import SnapshotCapabilities, SystemSnapshot


def _snap(cpu: float, mem_pct: float = 50.0) -> SystemSnapshot:
    total = 10_000_000_000
    used = int(total * mem_pct / 100.0)
    return SystemSnapshot(
        timestamp_monotonic_s=0.0,
        cpu_total_pct=cpu,
        mem_used_bytes=used,
        mem_total_bytes=total,
        swap_used_bytes=0,
        disk_read_bps=None,
        disk_write_bps=None,
        net_sent_bps=None,
        net_recv_bps=None,
        thermal_c=None,
        capabilities=SnapshotCapabilities(),
    )


def test_cpu_sustained_emits_once_per_episode():
    d = DetectionSettings(
        enabled=True,
        system_cpu_pct_above=80.0,
        system_cpu_sustained_ticks=3,
        memory_pct_above=None,
    )
    eng = DetectionEngine(d)
    buf = TickBuffer(maxlen=10)

    def tick(cpu: float) -> None:
        buf.append(TickRecord(_snap(cpu), ()))

    tick(90)
    assert eng.evaluate(buf) == []
    tick(90)
    assert eng.evaluate(buf) == []
    tick(90)
    sigs = eng.evaluate(buf)
    assert len(sigs) == 1
    assert sigs[0].kind == "high_system_cpu"

    # Still sustained — no repeat
    assert eng.evaluate(buf) == []

    # Recover (last 3 ticks must not all be above threshold)
    tick(10)
    assert eng.evaluate(buf) == []

    # New episode: need 3 consecutive high CPU ticks again
    tick(90)
    assert eng.evaluate(buf) == []
    tick(90)
    assert eng.evaluate(buf) == []
    tick(90)
    sigs2 = eng.evaluate(buf)
    assert len(sigs2) == 1
    assert sigs2[0].kind == "high_system_cpu"


def test_memory_rule_disabled_when_threshold_none():
    d = DetectionSettings(
        enabled=True,
        system_cpu_pct_above=None,
        memory_pct_above=90.0,
        memory_sustained_ticks=2,
    )
    eng = DetectionEngine(d)
    buf = TickBuffer(maxlen=10)
    buf.append(TickRecord(_snap(10.0, mem_pct=95.0), ()))
    buf.append(TickRecord(_snap(10.0, mem_pct=95.0), ()))
    sigs = eng.evaluate(buf)
    assert len(sigs) == 1
    assert sigs[0].kind == "high_memory_pressure"
