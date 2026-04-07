# Self-healing agent (local observability)

Cross-platform **observe → detect → diagnose → decide → act** agent. Core logic is OS-agnostic; **adapters** supply metrics (baseline: `psutil`).

## Docs

See the [`doc/`](./doc/) folder for architecture, product definition, and learning-first delivery process.

## Setup (development)

```bash
cd self_healing_agent
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

One sample tick (prints a short summary):

```bash
sha-agent once
```

Loop every 5 seconds:

```bash
sha-agent run --interval 5
```

Or:

```bash
python -m self_healing_agent once
```

## Test

```bash
pytest
```
# auto-system-healing-agent
