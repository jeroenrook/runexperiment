# Repository Guidelines

## Project Structure & Module Organization
- Core package: `runexperiment/` with `action.py` (Action definition), `experiment.py` (CLI/launch logic), `utils.py` (helpers), and `__main__.py` (CLI entry).
- CLI shim for legacy usage: `run_experiment.py`.
- Examples: `examples/driftas_experiment.py`.
- Configuration scaffold: `config.yaml` (created by `runexperiment init`).
- Tests: `tests/` for unit coverage of utils, CLI scaffolding, and invocation logic.
- Metadata: `pyproject.toml`, `.pre-commit-config.yaml`, `README.md`.

## Build, Test, and Development Commands
- Install (dev): `pip install -e ".[dev]"` — editable install with tooling.
- Scaffold starter files: `runexperiment init` (creates `experiment.py` and `config.yaml` in CWD).
- Run experiment script: `python my_experiment.py launch ...` or `runexperiment run ...`.
- Lint/format: `pre-commit run --all-files` (Ruff + Black + hygiene hooks).
- Tests: `pytest`.

## Coding Style & Naming Conventions
- Python style enforced by Ruff (lint, quick fixes) and Black (format). Default 4-space indent.
- Prefer explicit imports and small, focused modules (`action.py`, `experiment.py`, `utils.py`).
- CLI flags: kebab/long form (e.g., `--sbatch-array-limit`); Python variables snake_case.
- Result files live under `output/` and `results/` (configurable).

## Testing Guidelines
- Framework: `pytest`.
- Place tests in `tests/` with filenames like `test_<module>.py`.
- Use monkeypatching for external effects (e.g., SLURM env, subprocess) and avoid hitting cluster resources; mock `subprocess.run`/env vars.
- Run `pytest` locally before PRs; add regression tests for new public behaviors.

## Commit & Pull Request Guidelines
- Write clear, concise commit messages (imperative mood, e.g., "Add init scaffold CLI").
- For PRs: describe changes, note testing (`pytest`, `pre-commit`), and link issues if applicable. Include any behavioral risks (e.g., SLURM launch changes) and screenshots/log snippets only when relevant.

## Security & Configuration Tips
- Avoid committing secrets; configs like `config.yaml` contain SLURM params only.
- Validate paths passed to `--expdir/--targetdir`; scripts may generate SLURM batch files—confirm queue settings before submitting.
