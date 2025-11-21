#!/usr/bin/env python3
from abc import ABC
import itertools
import argparse
import pickle
import yaml
from pathlib import Path
import logging
import time
import copy
import multiprocessing as mp
import psutil
import shlex
import sys

from .action import Action
from .utils import get_cpus, run_local_worker


class Experiment(ABC):
    def __init__(
        self, experiment_space: dict, action_space: dict, pipelines: dict = None
    ):
        self.experiment_space = experiment_space
        self.action_space = action_space
        self.pipelines = pipelines

        self.args = None
        self._invocation = self._detect_invocation()

        self.main()

    def _detect_invocation(self) -> str:
        """Return the python command that should re-run this experiment script."""
        main_file = getattr(sys.modules.get("__main__"), "__file__", None)
        if main_file:
            return f"{shlex.quote(sys.executable)} {shlex.quote(str(Path(main_file).resolve()))}"
        return f"{shlex.quote(sys.executable)} -m runexperiment"

    # MAIN
    def main(self):
        self.args = self._parse_arguments()

        if self.args.modus is None:
            raise ValueError("Unknown experimental action!")

        modus = self.args.modus
        if modus == "launch":
            self.launch()
        elif modus == "run":
            self.run()
        elif modus == "pipeline":
            self.pipeline()

    def _parse_arguments(self):
        parser = argparse.ArgumentParser(
            prog="Experiment Controller",
            description="Generate, launch, validate and analyse experiments",
        )

        parser.add_argument("-c", "--config", default="config.yaml")

        parser.add_argument(
            "-d",
            "--expdir",
            required=False,
            default=None,
            help="Base directory to store the experimental scripts in",
            type=Path,
        )

        parser.add_argument(
            "-t",
            "--targetdir",
            required=False,
            default=None,
            help="Base directory to store results of an experiment in",
            type=Path,
        )

        parser.add_argument(
            "--sbatch",
            required=False,
            nargs=2,
            action="append",
            dest="sbatch_args",
            default=[],
        )

        parser.add_argument(
            "--sbatch-array-limit", required=False, type=int, dest="sbatch_array_limit"
        )

        parser.add_argument(
            "-n",
            "--name",
            default=None,
            required=False,
            help="Name of the experiment",
        )

        parser.add_argument(
            "-a",
            "--action",
            default=list(self.action_space.keys())[0],
            choices=self.action_space.keys(),
            help="Available actions",
            dest="action",
        )

        parser.set_defaults(dummy=True)
        parser.add_argument("--dummy", action="store_false")

        subparsers = parser.add_subparsers(
            help="The experiment modus: [launch, run]", dest="modus"
        )

        launch_parser = subparsers.add_parser("launch")
        run_parser = subparsers.add_parser("run")

        launch_parser.set_defaults(repair=False)
        launch_parser.add_argument(
            "-r",
            "--replace",
            help="Replace existing results. TODO implement",
            action="store_true",
        )

        launch_parser.set_defaults(repair=False)
        launch_parser.add_argument(
            "-f", "--repair", help="Repair failed results", action="store_true"
        )

        launch_parser.set_defaults(runlocal=False)
        launch_parser.add_argument("--local", action="store_true", dest="runlocal")

        for action_key, action in self.action_space.items():
            if len(action.expand) > 0:
                for argument in action.expand:
                    launch_parser.add_argument(
                        f"--{self.get_action_argument_name(action_key, argument)}",
                        required=False,
                        action="append",
                        nargs="+",
                        default=[],
                    )

                    run_parser.add_argument(
                        f"--{self.get_action_argument_name(action_key, argument)}",
                        required=False,
                        default=None,
                    )

        for key, options in self.experiment_space.items():
            option_names = [str(o) for o in options]
            launch_parser.add_argument(
                f"--{key}",
                required=False,
                action="append",
                nargs="+",
                default=[],
                choices=option_names,
            )
            run_parser.add_argument(f"--{key}", required=False, choices=option_names)

        args = parser.parse_args()
        action = self.action_space[args.action]

        if args.modus == "launch":
            for key, options in self.experiment_space.items():
                if not hasattr(args, key) or len(getattr(args, key)) == 0:
                    option_names = [str(o) for o in options]
                    setattr(args, key, option_names)
                elif isinstance(getattr(args, key), list):
                    option_names = []
                    for opt in getattr(args, key):
                        if isinstance(opt, str):
                            option_names.append(opt)
                        elif isinstance(opt, list):
                            option_names += opt
                    setattr(args, key, option_names)

            if len(action.expand) > 0:
                for argument in action.expand:
                    key = self.get_action_argument_name(args.action, argument)
                    if not hasattr(args, key):
                        continue
                    if isinstance(getattr(args, key), list):
                        option_names = []
                        for opt in getattr(args, key):
                            if isinstance(opt, str):
                                option_names.append(opt)
                            elif isinstance(opt, list):
                                option_names += opt
                        setattr(args, key, option_names)
                        if len(option_names) == 0:
                            delattr(args, key)

        if hasattr(args, "config"):
            config_file = Path(args.config)
            if config_file.exists():
                config = yaml.safe_load(config_file.read_text())
                for key, value in config.items():
                    if key == "sbatch":
                        sbatchkeys = [a[0] for a in args.sbatch_args]
                        for sbatchkey, sbatchval in value.items():
                            if sbatchkey not in sbatchkeys:
                                logging.info(
                                    f"Read sbatch value for {sbatchkey}={sbatchval} from config file."
                                )
                                args.sbatch_args.append((sbatchkey, sbatchval))
                    else:
                        if not hasattr(args, key) or getattr(args, key) is None:
                            logging.info(f"Read value for {key} from config file.")
                            setattr(args, key, value)

        if args.expdir is None:
            args.expdir = "./output"
        args.expdir = Path(args.expdir)
        if args.targetdir is None:
            args.targetdir = "./results"
        args.targetdir = Path(args.targetdir)

        basename = "" if args.name is None else args.name
        nameargs = [basename, args.modus, args.action]
        for key in self.experiment_space.keys():
            if key in action.reduce:
                continue
            if args.modus == "launch":
                if len(getattr(args, key)) == 1:
                    nameargs.append(getattr(args, key)[0])
                elif len(getattr(args, key)) == len(self.experiment_space[key]):
                    nameargs.append("all")
                else:
                    nameargs.append("multiple")
            elif args.modus == "run":
                nameargs.append(getattr(args, key))
        args.name = "_".join(nameargs)

        if args.modus == "run" and len(action.expand) > 0:
            for argument in action.expand:
                if not hasattr(
                    args, self.get_action_argument_name(args.action, argument)
                ):
                    raise ValueError(
                        f"action argument '{self.get_action_argument_name(args.action, argument)}' missing. Aborting run!"
                    )

        return args

    # HELPER FUNCTIONS
    def get_action(self, action=None) -> Action:
        action = self.args.action if action is None else action
        return self.action_space[action]

    def _get_dir(self, directory: Path, action: str = None):
        action = self.args.action if action is None else action
        return directory.joinpath(f"{action}/")

    def get_expdir(self, action: str = None):
        return self._get_dir(self.args.expdir, action)

    def get_targetdir(self, action: str = None):
        return self._get_dir(self.args.targetdir, action)

    def get_action_argument_name(self, action: str, argument: str):
        return f"{action}_{argument}"

    def get_exp_run_name(self, **kwargs):
        exp_name = []
        for key, item in kwargs.items():
            if key not in self.experiment_space.keys():
                raise ValueError(f"{key} not in experiment space!")
            exp_name.append(str(item).replace("_", "-"))
        return "_".join(exp_name)

    def get_actual_experiment(self, experiment_string: dict) -> dict:
        experiment = {}
        for key, string_val in experiment_string.items():
            option_names = [str(o) for o in self.experiment_space[key]]
            value_index = option_names.index(string_val)
            space = self.experiment_space[key]
            if isinstance(space, dict):
                experiment[key] = list(space.values())[value_index]
            else:
                experiment[key] = space[value_index]
        return experiment

    def save_result(self, result: dict, experiment: dict, **expand_arguments):
        actual_experiment = self.get_actual_experiment(experiment)

        result = {
            "experiment": {k: str(v) for k, v in experiment.items()},
            "actual_experiment": actual_experiment,
            "run_result": result,
            "action": self.args.action,
            "timestamp": time.time(),
        }

        if len(expand_arguments) == 0:
            self.get_targetdir().mkdir(parents=True, exist_ok=True)
            result_file = self.get_targetdir().joinpath(
                f"{self.get_exp_run_name(**experiment)}.pickle"
            )
        else:
            result["expand_arguments"] = expand_arguments
            result_dir = self.get_targetdir().joinpath(
                f"{self.get_exp_run_name(**experiment)}/"
            )
            result_dir.mkdir(parents=True, exist_ok=True)
            filename = "_".join([str(v) for v in expand_arguments.values()])
            filename = f"{filename}.pickle"
            result_file = result_dir.joinpath(filename)

        with open(result_file, "wb") as fh:
            pickle.dump(result, fh, protocol=5)

    def get_result(self, experiment: dict, action: str, **expand_args):
        action = self.get_action(action)
        exp_name = self.get_exp_run_name(**experiment)

        if len(expand_args) > 0:
            expand_args = {
                k: v if isinstance(v, list) else list(v) for k, v in expand_args.items()
            }

        if len(action.expand) == 0:
            result_file = self.get_targetdir(action.name).joinpath(f"{exp_name}.pickle")
            if not result_file.exists():
                message = f"File '{result_file}' does not exist. Please launch the action {action.name} on {exp_name} first."
                raise FileExistsError(message)
            with open(result_file, "rb") as fh:
                result = pickle.load(fh)

            if "run_result" not in result.keys():
                result = {
                    "experiment": {k: str(v) for k, v in experiment.items()},
                    "run_result": result,
                    "action": action,
                }
            return result
        else:
            result_dir = self.get_targetdir(action.name).joinpath(f"{exp_name}/")
            if not result_dir.exists():
                message = f"Directory '{result_dir}' does not exist. Please launch the action {action.name} on {exp_name} first."
                raise FileExistsError(message)
            result = None
            for result_file in result_dir.iterdir():
                with open(result_file, "rb") as fh:
                    res = pickle.load(fh)

                if len(expand_args) > 0:
                    rea = res["expand_arguments"]
                    if not all(
                        [
                            str(rea[k]) in expand_args[k]
                            for k in rea.keys()
                            if k in expand_args.keys()
                        ]
                    ):
                        continue

                if result is None:
                    result = copy.copy(res)
                    result["expand_arguments"] = list(result["expand_arguments"].keys())
                    result["run_result"] = {}

                result["run_result"][tuple(res["expand_arguments"].items())] = res[
                    "run_result"
                ]

            return result

    # Actions
    def launch(self):
        args = self.args

        combinations = []
        experiment_space_keys = []
        reduce_combinations = {}
        for key in self.experiment_space.keys():
            if len(self.get_action().reduce) > 0 and key in self.get_action().reduce:
                reduce_combinations[key] = getattr(args, f"{key}")
                continue
            combinations.append(getattr(args, key))
            experiment_space_keys.append(key)

        action = self.get_action()

        kwarg_filter = {}
        for arg in action.expand:
            expand_key = self.get_action_argument_name(str(action), arg)
            if hasattr(args, expand_key):
                kwarg_filter[arg] = getattr(args, expand_key)

        possible_runs = 0
        actual_runs = 0
        run_arguments = []

        for run in itertools.product(*combinations):
            run_args = " ".join(
                [f"--{k} {v}" for k, v in zip(experiment_space_keys, run)]
            )
            experiment = {k: v for k, v in zip(experiment_space_keys, run)}
            key_experiment = experiment
            experiment = self.get_actual_experiment(experiment)

            if len(action.expand) > 0:
                result_dir = self.get_targetdir().joinpath(
                    f"{self.get_exp_run_name(**key_experiment)}/"
                )
                kwargs_runs = action.expand_fn(experiment, self)
                for kwarg_run in kwargs_runs:
                    if not all(
                        [
                            str(v) in kwarg_filter[k]
                            for k, v in zip(action.expand, kwarg_run)
                            if k in kwarg_filter
                        ]
                    ):
                        continue

                    possible_runs += 1

                    if result_dir.exists():
                        filename = "_".join([str(v) for v in kwarg_run])
                        filename = f"{filename}.pickle"
                        result_file = result_dir.joinpath(filename)
                        if args.repair and result_file.exists():
                            if action.check_complete is not None:
                                with open(str(result_file), "rb") as fh:
                                    result = pickle.load(fh)
                                if action.check_complete(result["run_result"]):
                                    continue
                                else:
                                    print(f"Incomplete results found in {result_file}")
                            else:
                                continue

                        if args.dummy and result_file.exists():
                            result_file.unlink(missing_ok=True)

                    kwarg_args = " ".join(
                        [
                            f"--{self.get_action_argument_name(args.action, k)} {v}"
                            for k, v in zip(action.expand, kwarg_run)
                        ]
                    )
                    run_arguments.append(f"{run_args} {kwarg_args}")
                    actual_runs += 1
            else:
                possible_runs += 1
                result_file = self.get_targetdir().joinpath(
                    f"{self.get_exp_run_name(**key_experiment)}.pickle"
                )
                if result_file.exists():
                    if args.repair and action.check_complete is not None:
                        with open(str(result_file), "rb") as fh:
                            result = pickle.load(fh)
                        if action.check_complete(result["run_result"]):
                            continue
                    elif args.repair and result_file.exists():
                        continue

                    if args.dummy:
                        result_file.unlink()
                run_arguments.append(run_args)
                actual_runs += 1

        print(f"Total number of independent runs={len(run_arguments)}")
        pass_args_on = f"--name {args.name} --expdir {args.expdir} --targetdir {args.targetdir} --config {args.config}"
        if len(run_arguments) == 0:
            print("No runs to launch.")
            return

        # directories
        exp_dir_path = Path(args.expdir).joinpath(args.action)
        exp_dir_path.mkdir(parents=True, exist_ok=True)
        target_dir_path = Path(args.targetdir).joinpath(args.action)
        target_dir_path.mkdir(parents=True, exist_ok=True)

        if args.runlocal and args.dummy:
            run_commands = [
                f"{self._invocation} --action {args.action} {pass_args_on} run {r}"
                for r in run_arguments
            ]
            with mp.Pool(max(get_cpus() - 1, 1)) as pool:
                pool.map(run_local_worker, run_commands)
            return

        chunksize = 1000
        chunkid = 0
        timestamp = int(time.time())
        while chunkid * chunksize < len(run_arguments):
            launch_name = f"launch_{timestamp}_{chunkid}.sh"
            chunk_start = chunkid * chunksize
            chunk_end = min(chunk_start + chunksize - 1, len(run_arguments) - 1)

            sbatch_args = []
            sbatch_args.append(f"--job-name=exp_{args.name}_{chunkid}")
            for sbatchkey, sbatchval in args.sbatch_args:
                sbatch_args.append(f"--{sbatchkey}={sbatchval}")
            logoutput = exp_dir_path.joinpath(f"{args.name}_{chunkid}_%a.out")
            sbatch_args.append(f"--output={logoutput}")
            sbatch_args.append(f"--array=0-{chunk_end - chunk_start}")
            if hasattr(args, "sbatch_array_limit"):
                sbatch_args[-1] += f"%{args.sbatch_array_limit}"

            script = ["#!/usr/bin/bash"]
            script += [f"#SBATCH {line}" for line in sbatch_args]
            script.append("")
            script.append(
                'experiment=( "'
                + '" \\\n"'.join(run_arguments[chunk_start : chunk_end + 1])
                + '" )'
            )
            script.append("")
            script.append(
                "echo \"START runexperiment call at $(date '+%Y-%m-%d %H:%M:%S')\""
            )
            script.append(
                f"{self._invocation} --action {args.action} {pass_args_on} run ${{experiment[$SLURM_ARRAY_TASK_ID]}}"
            )
            if len(run_arguments) > chunk_end + 1:
                script.append("")
                script.append(
                    f'if [[ "$SLURM_ARRAY_TASK_ID" -eq {chunk_end - chunk_start} ]]\nthen'
                )
                script.append(f"\tsbatch launch_{timestamp}_{chunkid+1}.sh")
                script.append("fi")

            if args.dummy:
                with open(launch_name, "w") as fh:
                    fh.write("\n".join(script) + "\n")
                Path(launch_name).chmod(0o755)
                if chunkid == 0:
                    import subprocess

                    subprocess.run(["sbatch", launch_name])
            else:
                print("\n".join(script))
            chunkid += 1
        print(
            f"There were {possible_runs} possible runs of which {actual_runs} were queued."
        )

    def run(self):
        args = self.args
        action = self.get_action()

        experiment = {
            k: getattr(args, f"{k}")
            for k in self.experiment_space.keys()
            if k not in action.reduce
        }
        experiment_name = self.get_exp_run_name(**experiment)
        setattr(self.args, "experiment_name", experiment_name)

        actual_experiment = self.get_actual_experiment(experiment)

        action_arguments = {}
        if len(action.expand) > 0:
            for argument in action.expand:
                argument_name = self.get_action_argument_name(action.name, argument)
                if not hasattr(args, argument_name):
                    raise ValueError(f"Expected the argument '{argument_name}'.")
                action_arguments[argument] = getattr(args, argument_name)

        print(
            f"[START RUN] Current Time: {time.strftime('%Y-%m-%d %H:%M:%S')}, CPU Usage: {psutil.cpu_percent()}%, Memory Usage: {psutil.virtual_memory().percent}%"
        )

        result = action.fn(actual_experiment, self, **action_arguments)

        print(
            f"[END RUN] Current Time: {time.strftime('%Y-%m-%d %H:%M:%S')}, CPU Usage: {psutil.cpu_percent()}%, Memory Usage: {psutil.virtual_memory().percent}%"
        )

        self.save_result(result, experiment, **action_arguments)

        if action.callback is not None:
            action.callback(actual_experiment, self, **action_arguments)

    def pipeline(self):
        raise NotImplementedError
