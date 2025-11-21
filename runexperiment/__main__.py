import argparse
import logging
from pathlib import Path
import textwrap


def _write_file(
    path: Path, content: str, executable: bool = False, force: bool = False
) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Use --force to overwrite.")
    path.write_text(content)
    if executable:
        path.chmod(path.stat().st_mode | 0o111)


def _experiment_template() -> str:
    return textwrap.dedent(
        """\
        #!/usr/bin/env python3
        from runexperiment import Action, Experiment


        # Define your experiment search space
        exp_space = {
            "dataset": ["example_dataset"],
            "seed": [0, 1],
        }


        # Define the function to execute for each configuration
        def run_task(experiment, exp: Experiment):
            # experiment is a dict with concrete values pulled from exp_space
            return {"status": "ok", "experiment": experiment}


        if __name__ == "__main__":
            actions = {"run_task": Action("run_task", run_task)}
            Experiment(exp_space, actions)
        """
    )


def _config_template() -> str:
    return textwrap.dedent(
        """\
        # Default configuration for runexperiment
        # Values here are merged into CLI args if not provided explicitly.
        sbatch:
          time: "01:00:00"
          mem: "4G"
          cpus-per-task: "1"
        expdir: "./output"
        targetdir: "./results"
        """
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="runexperiment",
        description="Utilities for running experiment grids locally or on SLURM.",
    )
    sub = parser.add_subparsers(dest="command")

    init_parser = sub.add_parser(
        "init", help="Create a starter experiment.py and config.yaml."
    )
    init_parser.add_argument(
        "--dest",
        type=Path,
        default=Path("."),
        help="Directory to place generated files (default: current directory).",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files if they already exist.",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.command == "init":
        dest: Path = args.dest
        dest.mkdir(parents=True, exist_ok=True)

        experiment_path = dest / "experiment.py"
        config_path = dest / "config.yaml"

        _write_file(
            experiment_path, _experiment_template(), executable=True, force=args.force
        )
        logging.info("Created %s", experiment_path)

        _write_file(config_path, _config_template(), force=args.force)
        logging.info("Created %s", config_path)
        return

    print(
        "runexperiment is packaged as a library. "
        "Import Action/Experiment and define your own experiment script "
        "(see README.md). For the previous DriftAS setup, run examples/driftas_experiment.py. "
        "Run `runexperiment init` to scaffold a starter script and config."
    )


if __name__ == "__main__":
    main()
