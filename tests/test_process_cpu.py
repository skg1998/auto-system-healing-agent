from self_healing_agent.adapters.process_cpu import (
    normalize_cpu_to_machine_share,
    should_skip_process_for_ranking,
)


def test_skip_system_idle_windows():
    assert should_skip_process_for_ranking(0, "System Idle Process") is True
    assert should_skip_process_for_ranking(0, "system idle process") is True


def test_normalize_multi_core():
    assert normalize_cpu_to_machine_share(400.0, 8) == 50.0
    assert normalize_cpu_to_machine_share(100.0, 0) == 100.0
