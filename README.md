# RunExperiment

Utilities for defining an experiment space and launching runs locally or on a SLURM cluster. The core `Experiment` class handles argument parsing, result bookkeeping and SLURM array script generation so you can focus on defining what each run should execute.

## Install

From the repository root:

```bash
pip install .
# or in editable mode while developing:
pip install -e .
```

Create a starter experiment script and config:

```bash
runexperiment init
# or python -m runexperiment init
```

## Development

- Install dev tools (quote extras to avoid shell globbing): `pip install -e ".[dev]"`
- Enable git hooks: `pre-commit install`
- Run checks manually: `pre-commit run --all-files`
- Run tests: `pytest`

## Basic usage

```python
from runexperiment import Action, Experiment

exp_space = {"dataset": ["a", "b"], "seed": [0, 1]}


def train(experiment, exp: Experiment):
    # experiment == {"dataset": "a", "seed": 0} with actual objects if you provided them
    return {"metrics": {"loss": 0.1}}


if __name__ == "__main__":
    actions = {"train": Action("train", train)}
    Experiment(exp_space, actions)
```

If your script lives in `my_experiment.py`, run:

```bash
python my_experiment.py launch --action train --dataset a --seed 0
# or run a single configuration:
python my_experiment.py run --action train --dataset a --seed 0
```

See `runexperiment/experiment.py` for the full set of CLI options (including SLURM arguments) and an end-to-end example.
When launching to SLURM, `--sbatch-commands-per-task N` will sequentially execute N run commands inside each array task (default 1) so you can reduce scheduler overhead.
