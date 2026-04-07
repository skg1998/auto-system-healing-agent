# Milestone P0–P1 (first code slice)

## What exists in the repo

| Piece | Location | Role |
|-------|----------|------|
| **Domain models** | `src/self_healing_agent/core/models.py` | `SystemSnapshot`, `ProcessSample`, `SnapshotCapabilities` — OS-agnostic shapes |
| **Tick buffer** | `src/self_healing_agent/core/buffer.py` | Rolling `TickRecord` history for later “sustained” detection |
| **Ports** | `src/self_healing_agent/ports/collectors.py` | `IMetricsCollector`, `IProcessInspector` (Protocols) |
| **Fake adapter** | `src/self_healing_agent/adapters/fake.py` | Deterministic metrics for tests (no OS calls) |
| **Psutil adapter** | `src/self_healing_agent/adapters/psutil_adapter.py` | Baseline metrics on **Windows / Linux / macOS** via **psutil** |
| **Pipeline** | `src/self_healing_agent/application/pipeline.py` | One **tick** = system snapshot + process list → buffer |
| **CLI** | `src/self_healing_agent/cli.py` | `once` and `run` commands |

## How to run

From repo root (after venv + `pip install -e ".[dev]"`):

```bash
python -m self_healing_agent once
python -m self_healing_agent run --interval 5
```

If the `sha-agent` console script fails to install on Windows (permissions), use `python -m self_healing_agent` as above.

## Tests

```bash
pytest
```

## What to learn on this step (systems angle)

1. **Why two phases for process CPU%** — The OS does not give “instant” per-process CPU; you compare usage over a **time window** (we prime `cpu_percent`, sleep briefly, then read again). Same idea on all OSes; psutil hides the syscalls.
2. **Disk/network “bytes per second”** — Needs **two samples** and \(\Delta\text{bytes}/\Delta t\). First tick may show `n/a` for rates until a second tick exists.
3. **Ports vs adapters** — Core only sees `SystemSnapshot` / `ProcessSample`. Swapping **psutil** for WMI-only or a Linux `/proc` reader later does not change the pipeline’s shape.

## Next milestone (P2)

- Config file (YAML) + validation.
- **Detection** rules (sustained CPU/RAM) + **notifications** only (no auto-kill).

See [06-roadmap-and-testing.md](./06-roadmap-and-testing.md).
