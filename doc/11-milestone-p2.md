# Milestone P2 — config, detection, notify (log)

## What shipped

| Piece | Location |
|-------|----------|
| **YAML config + validation** | `src/self_healing_agent/config/` (`AppConfig`, `load_config`) |
| **Default config file** | `config/default.yaml` |
| **Detection** | `src/self_healing_agent/core/detection.py` — sustained system CPU & memory % |
| **Notifier port** | `src/self_healing_agent/ports/notifier.py` |
| **Logging notifier** | `src/self_healing_agent/adapters/logging_notifier.py` (optional `--dry-run`) |
| **Run loop** | `src/self_healing_agent/application/runner.py` |
| **CLI** | `run --config`, `--dry-run`, `--quiet`, `--interval` |

## Behavior

- **Sustained** means the last **K** consecutive ticks in the buffer all exceed the threshold (not a single spike).
- **One notification per episode**: when the condition clears, the next sustained episode can notify again.
- **No process kill** in P2 — only log warnings (real or `[DRY]`).

## Learn

- **Why thresholds use ticks, not wall-clock seconds:** the buffer is “one sample per tick”; tie **K** to **interval** mentally (e.g. 3 ticks × 5 s ≈ 15 s).
- **Disabling a rule:** set `system_cpu_pct_above: null` or `memory_pct_above: null` in YAML.

## Next (P3)

Multi-signal **diagnosis** (confidence + correlation), still notify-first.
