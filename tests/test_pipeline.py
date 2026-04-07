from self_healing_agent.adapters.fake import FakeMetricsAdapter
from self_healing_agent.application.pipeline import Pipeline
from self_healing_agent.core.buffer import TickBuffer
from self_healing_agent.core.models import ProcessSample, SnapshotCapabilities, SystemSnapshot


def test_pipeline_tick_appends_to_buffer():
    snap = SystemSnapshot(
        timestamp_monotonic_s=42.0,
        cpu_total_pct=7.0,
        mem_used_bytes=1,
        mem_total_bytes=2,
        swap_used_bytes=0,
        disk_read_bps=None,
        disk_write_bps=None,
        net_sent_bps=None,
        net_recv_bps=None,
        thermal_c=None,
        capabilities=SnapshotCapabilities(),
    )
    procs = [
        ProcessSample(
            pid=1,
            parent_pid=None,
            name="a",
            cpu_pct=1.0,
            rss_bytes=100,
            thread_count=1,
        )
    ]
    adapter = FakeMetricsAdapter(snapshot=snap, processes=procs)
    buf = TickBuffer()
    pipe = Pipeline(adapter, adapter, buf)

    rec = pipe.tick()
    assert rec.snapshot.cpu_total_pct == 7.0
    assert len(rec.processes) == 1
    assert buf.latest() is rec
