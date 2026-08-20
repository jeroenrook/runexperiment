#!/usr/bin/env python3
from runexperiment import Action, Experiment
import time
import numpy as np

# Define your experiment search space
exp_space = {
    "dataset": ["example_dataset", "example_dataset2"],
    "seed": range(100),
}


# Define the function to execute for each configuration
def run_task(experiment, exp: Experiment):
    # experiment is a dict with concrete values pulled from exp_space
    print("RUN TASK")
    print(experiment)
    t = 1 + np.random.random()
    time.sleep(t)
    return {"status": "ok", "experiment": experiment}


def run_figure(experiment, exp: Experiment):
    # experiment is a dict with concrete values pulled from exp_space
    print("RUN FIGURE")
    print(experiment)
    t = 1 + np.random.random()
    time.sleep(t)
    return {"status": "ok", "experiment": experiment}


if __name__ == "__main__":
    actions = {
        "run_task": Action("run_task", run_task, check_complete=True),
        "run_figure": Action("run_figure", run_figure, check_complete=True),
    }
    Experiment(exp_space, actions)
