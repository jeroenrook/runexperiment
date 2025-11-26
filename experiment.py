#!/usr/bin/env python3
from runexperiment import Action, Experiment
import time
import numpy as np

# Define your experiment search space
exp_space = {
    "dataset": ["example_dataset"],
    "seed": range(100),
}


# Define the function to execute for each configuration
def run_task(experiment, exp: Experiment):
    # experiment is a dict with concrete values pulled from exp_space
    t = 1 + np.random.random()
    time.sleep(t)
    return {"status": "ok", "experiment": experiment}


if __name__ == "__main__":
    actions = {"run_task": Action("run_task", run_task)}
    Experiment(exp_space, actions)
