#!/usr/bin/env python3
import numpy as np

from runexperiment import Action, Experiment

datasets = "a,b,c,d,e,f,g".split(",")


def configure(experiment, expclass: Experiment):
    test_dataset = [experiment["dataset"]]
    _train_dataset = [d for d in datasets if d not in test_dataset]

    _seed = experiment["smac_seed"]

    # Run SMAC

    return {"config": np.random.random()}


def get_datasets(*args, **kwargs):
    # Expand functions can make additional paralellizable jobs that are dependent on the experiment that is being ran
    return datasets


def validate(experiment, expclass: Experiment):
    result = expclass.get_result(experiment, "configure")
    _instance = experiment["validate_instance"]

    return {"accuracy": np.random.random() + result["config"]}


if __name__ == "__main__":

    experimental_space = {
        "dataset": datasets + ["all"],
        "smac_seed": range(15),
    }

    actions = {
        "configure": Action("configure", configure),
        "validate": Action(
            "validate", validate, expand=["instance"], expand_fn=get_datasets
        ),
    }

    Experiment(experimental_space, actions)
