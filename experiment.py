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
