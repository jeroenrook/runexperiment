# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install with dev tools (editable)
pip install -e ".[dev]"

# Run tests
pytest

# Run a single test
pytest tests/test_experiment_invocation.py::test_name

# Lint and format
pre-commit run --all-files

# Scaffold starter files in current directory
runexperiment init
```

The virtual environment is in `.venv`. Activate with `source .venv/bin/activate` before running Python commands.

## Architecture

`runexperiment` turns an experiment parameter grid into CLI-driven runs that can execute locally or on SLURM.

### Core flow

Calling `Experiment(exp_space, actions)` immediately runs `__init__` → `main()` → `_parse_arguments()`, which parses `sys.argv` and dispatches to one of three modes:

- **`launch`**: Computes the Cartesian product of `exp_space` parameters, skips already-completed results, then either (a) runs all configs locally in a multiprocessing pool with a tqdm progress bar, or (b) generates SLURM `sbatch` array scripts and submits the first chunk immediately. Large parameter spaces are chunked into files of ≤1000 tasks; each chunk's script submits the next chunk when its last task completes.
- **`run`**: Executes a single configuration by calling `action.fn(actual_experiment, self, **action_arguments)` and pickling the result under `targetdir/<action>/<exp_name>.pickle`.
- **`pipeline`**: Not yet implemented.

### Key classes

**`Action`** (`action.py`): Metadata wrapper around a callable. Key fields:
- `fn`: the function to call per run — signature `fn(experiment: dict, exp: Experiment, **expand_args)`
- `reduce`: list of experiment-space keys to *exclude* from the Cartesian product (used for aggregation actions)
- `expand`: list of extra argument names that are iterated over separately (e.g. seeds within a run); `expand_fn(experiment, exp)` produces tuples of values
- `check_complete(result)`: optional callable to detect incomplete/failed results (used with `--repair`)

**`Experiment`** (`experiment.py`): Abstract base class. Users subclass it or instantiate it directly. The constructor drives the whole CLI lifecycle. Useful methods for use inside `fn`:
- `save_result(result, experiment, **expand_args)` — pickle result
- `get_result(experiment, action, **expand_args)` — load pickled result
- `get_exp_run_name(**kwargs)` — canonical string key for a config
- `get_targetdir(action)` / `get_expdir(action)` — resolved output paths

### Config and CLI layering

Arguments are resolved in this priority order (highest wins): CLI flags → `config.yaml` values → hardcoded defaults. The config file path defaults to `config.yaml` and is read in `_parse_arguments`. `sbatch` keys in the config file are merged with `--sbatch KEY VALUE` flags, with CLI flags taking precedence.

### Result storage layout

```
results/<action>/<exp_name>.pickle          # no expand
results/<action>/<exp_name>/<expand_vals>.pickle  # with expand
```

Results are dicts with keys: `experiment`, `actual_experiment`, `run_result`, `action`, `timestamp` (and `expand_arguments` when applicable).

### experiment_space values

Values in `exp_space` can be plain lists *or* dicts. When a dict, the keys are string labels used on the CLI and in filenames; the values are the actual objects passed to `fn`. This allows passing non-serialisable objects (like class instances) while keeping CLI args human-readable.

## Code style

Ruff (lint + auto-fix) and Black (format) are enforced via pre-commit. Line length is 79 characters (PEP 8).
