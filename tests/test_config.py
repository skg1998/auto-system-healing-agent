from pathlib import Path

from self_healing_agent.config.load import load_config


def test_load_default_yaml(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        """
version: 1
agent:
  tick_interval_seconds: 2.0
detection:
  enabled: true
  system_cpu_pct_above: 70.0
  system_cpu_sustained_ticks: 2
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.agent.tick_interval_seconds == 2.0
    assert cfg.detection.system_cpu_pct_above == 70.0
    assert cfg.detection.system_cpu_sustained_ticks == 2
