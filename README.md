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

If `pip install -e` fails to write `sha-agent.exe` (permissions), use `python -m self_healing_agent` instead of the `sha-agent` command.

## Run

Print version: `python -m self_healing_agent --version` (or `-V`).

**One sample tick** (prints a short summary):

```bash
python -m self_healing_agent once
```

**Loop** with defaults (built-in config):

```bash
python -m self_healing_agent run
```

**Loop** with YAML config (see `config/default.yaml`):

```bash
python -m self_healing_agent run --config config/default.yaml
```

**Dry-run** (log alerts as `[DRY]`):

```bash
python -m self_healing_agent run --config config/default.yaml --dry-run
```

**Quiet** (less per-tick metrics; detection still runs):

```bash
python -m self_healing_agent run --quiet
```

Override tick interval only (seconds):

```bash
python -m self_healing_agent run --interval 5
```

## Test

```bash
pytest
```

`pytest.ini` sets `pythonpath = src` so tests always import the package from this repo.

**Lint (optional, matches CI):** from the repo root after `pip install -e ".[dev]"`:

```bash
python -m ruff check src tests
python -m ruff format --check src tests
```

**Pre-commit (optional):** `pip install pre-commit && pre-commit install` — runs Ruff on commit. Use `pre-commit run --all-files` to check once.

Pushes and pull requests run **lint + tests** on GitHub Actions (Ubuntu, Windows, macOS).
