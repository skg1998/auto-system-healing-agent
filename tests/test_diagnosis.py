from self_healing_agent.config.models import DetectionSettings, DiagnosisSettings
from self_healing_agent.core.buffer import TickBuffer, TickRecord
from self_healing_agent.core.detection import DetectionEngine, DetectionSignal
from self_healing_agent.core.diagnosis import DiagnosisEngine
from self_healing_agent.core.models import ProcessSample, SnapshotCapabilities, SystemSnapshot


def _proc(pid: int, name: str, cpu: float, rss: int) -> ProcessSample:
    return ProcessSample(
        pid=pid,
        parent_pid=None,
        name=name,
        cpu_pct=cpu,
        rss_bytes=rss,
        thread_count=None,
    )


def _snap(
    cpu: float,
    *,
    mem_pct: float = 50.0,
    disk_r: float | None = 0.0,
    disk_w: float | None = 0.0,
    net_up: float | None = 0.0,
    net_dn: float | None = 0.0,
) -> SystemSnapshot:
    total = 10_000_000_000
    used = int(total * mem_pct / 100.0)
    return SystemSnapshot(
        timestamp_monotonic_s=0.0,
        cpu_total_pct=cpu,
        mem_used_bytes=used,
        mem_total_bytes=total,
        swap_used_bytes=0,
        disk_read_bps=disk_r,
        disk_write_bps=disk_w,
        net_sent_bps=net_up,
        net_recv_bps=net_dn,
        thermal_c=None,
        capabilities=SnapshotCapabilities(),
    )


def test_diagnosis_disabled_returns_empty():
    eng = DiagnosisEngine(DiagnosisSettings(enabled=False))
    buf = TickBuffer(maxlen=5)
    buf.append(TickRecord(_snap(90.0), ()))
    sigs = [
        DetectionSignal(kind="high_system_cpu", message="x"),
    ]
    assert eng.diagnose(buf, sigs) == []


def test_cpu_low_io_compute_path():
    eng = DiagnosisEngine(
        DiagnosisSettings(disk_io_high_bps=5_000_000.0, net_io_high_bps=5_000_000.0)
    )
    buf = TickBuffer(maxlen=5)
    buf.append(
        TickRecord(
            _snap(90.0, disk_r=1e6, disk_w=1e6, net_up=1e6, net_dn=1e6),
            (_proc(1, "worker", 40.0, 100_000_000),),
        )
    )
    sigs = [DetectionSignal(kind="high_system_cpu", message="cpu high")]
    hyps = eng.diagnose(buf, sigs)
    assert len(hyps) == 1
    assert hyps[0].hypothesis_id == "cpu_compute_bound"
    assert hyps[0].confidence == 0.45
    assert "worker" in hyps[0].summary


def test_cpu_high_disk_io_path():
    eng = DiagnosisEngine(
        DiagnosisSettings(disk_io_high_bps=5_000_000.0, net_io_high_bps=5_000_000.0)
    )
    buf = TickBuffer(maxlen=5)
    buf.append(
        TickRecord(
            _snap(90.0, disk_r=4_000_000.0, disk_w=4_000_000.0),
            (),
        )
    )
    sigs = [DetectionSignal(kind="high_system_cpu", message="cpu high")]
    hyps = eng.diagnose(buf, sigs)
    assert hyps[0].hypothesis_id == "cpu_disk_io"
    assert hyps[0].confidence == 0.56


def test_cpu_disk_and_net_path():
    eng = DiagnosisEngine(
        DiagnosisSettings(disk_io_high_bps=5_000_000.0, net_io_high_bps=5_000_000.0)
    )
    buf = TickBuffer(maxlen=5)
    buf.append(
        TickRecord(
            _snap(
                90.0, disk_r=4_000_000.0, disk_w=4_000_000.0, net_up=4_000_000.0, net_dn=4_000_000.0
            ),
            (),
        )
    )
    sigs = [DetectionSignal(kind="high_system_cpu", message="cpu high")]
    hyps = eng.diagnose(buf, sigs)
    assert hyps[0].hypothesis_id == "cpu_disk_net"
    assert hyps[0].confidence == 0.58


def test_memory_hypothesis():
    eng = DiagnosisEngine(DiagnosisSettings())
    buf = TickBuffer(maxlen=5)
    buf.append(
        TickRecord(
            _snap(10.0, mem_pct=95.0),
            (_proc(7, "chrome", 1.0, 3_000_000_000),),
        )
    )
    sigs = [DetectionSignal(kind="high_memory_pressure", message="mem high")]
    hyps = eng.diagnose(buf, sigs)
    assert len(hyps) == 1
    assert hyps[0].hypothesis_id == "memory_rss"
    assert "chrome" in hyps[0].summary


def test_cpu_and_memory_includes_combo_sorted():
    eng = DiagnosisEngine(DiagnosisSettings())
    buf = TickBuffer(maxlen=5)
    buf.append(
        TickRecord(
            _snap(90.0, mem_pct=95.0),
            (),
        )
    )
    sigs = [
        DetectionSignal(kind="high_system_cpu", message="cpu"),
        DetectionSignal(kind="high_memory_pressure", message="mem"),
    ]
    hyps = eng.diagnose(buf, sigs)
    ids = [h.hypothesis_id for h in hyps]
    assert "cpu_memory_combined" in ids
    assert hyps[0].hypothesis_id == "cpu_memory_combined"
    assert hyps[0].confidence == 0.62


def test_empty_signals_returns_empty():
    eng = DiagnosisEngine(DiagnosisSettings())
    buf = TickBuffer(maxlen=5)
    buf.append(TickRecord(_snap(90.0), ()))
    assert eng.diagnose(buf, []) == []


def test_detection_plus_diagnosis_integration():
    """Sustained CPU triggers detection signal; diagnosis explains same tick."""
    d = DetectionSettings(
        enabled=True,
        system_cpu_pct_above=80.0,
        system_cpu_sustained_ticks=3,
        memory_pct_above=None,
    )
    detector = DetectionEngine(d)
    diag = DiagnosisEngine(DiagnosisSettings())
    buf = TickBuffer(maxlen=10)

    def tick(cpu: float) -> None:
        buf.append(
            TickRecord(_snap(cpu, disk_r=1e6, disk_w=1e6), (_proc(2, "app", 50.0, 10_000_000),))
        )

    tick(90)
    tick(90)
    tick(90)
    sigs = detector.evaluate(buf)
    assert len(sigs) == 1
    hyps = diag.diagnose(buf, sigs)
    assert len(hyps) >= 1
    assert hyps[0].hypothesis_id == "cpu_compute_bound"
