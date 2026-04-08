from self_healing_agent.adapters.linux.ranking import (
    filter_linux_process_ranking,
    should_skip_linux_ranking,
)
from self_healing_agent.core.models import ProcessSample


def _sample(pid: int, name: str) -> ProcessSample:
    return ProcessSample(
        pid=pid,
        parent_pid=None,
        name=name,
        cpu_pct=1.0,
        rss_bytes=1000,
        thread_count=None,
    )


def test_skip_kthreadd_name():
    assert should_skip_linux_ranking("kthreadd") is True
    assert should_skip_linux_ranking("KTHREADD") is True
    assert should_skip_linux_ranking("bash") is False


def test_filter_removes_kthreadd():
    rows = [
        _sample(2, "kthreadd"),
        _sample(100, "bash"),
    ]
    out = filter_linux_process_ranking(rows)
    assert len(out) == 1
    assert out[0].name == "bash"
