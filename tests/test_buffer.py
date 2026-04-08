from self_healing_agent.core.buffer import TickBuffer, TickRecord
from self_healing_agent.core.models import SnapshotCapabilities, SystemSnapshot


def _snap(ts: float = 1.0) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp_monotonic_s=ts,
        cpu_total_pct=50.0,
        mem_used_bytes=100,
        mem_total_bytes=200,
        swap_used_bytes=0,
        disk_read_bps=None,
        disk_write_bps=None,
        net_sent_bps=None,
        net_recv_bps=None,
        thermal_c=None,
        capabilities=SnapshotCapabilities(),
    )


def test_tick_buffer_maxlen_evicts_oldest():
    buf = TickBuffer(maxlen=2)
    buf.append(TickRecord(_snap(1.0), ()))
    buf.append(TickRecord(_snap(2.0), ()))
    buf.append(TickRecord(_snap(3.0), ()))
    items = list(buf.iter_recent())
    assert len(items) == 2
    assert items[0].snapshot.timestamp_monotonic_s == 2.0
    assert items[1].snapshot.timestamp_monotonic_s == 3.0


def test_latest():
    buf = TickBuffer()
    assert buf.latest() is None
    r = TickRecord(_snap(5.0), ())
    buf.append(r)
    assert buf.latest() is r


def test_iter_recent_last_n():
    buf = TickBuffer(maxlen=10)
    for i in range(1, 6):
        buf.append(TickRecord(_snap(float(i)), ()))
    last3 = list(buf.iter_recent(last_n=3))
    assert [t.snapshot.timestamp_monotonic_s for t in last3] == [3.0, 4.0, 5.0]
