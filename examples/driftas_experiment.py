import logging
import os
import time

from tqdm import tqdm

from runexperiment import Action, Experiment
from driftas.stream import (
    StreamGeneratorSudden,
    StreamGeneratorRecurrent,
    StreamGeneratorSmooth,
)
from driftas.selectors import StreamAS, FixedSelector, RandomSelector, MABSelector


def main():
    """Run the original DriftAS experiment setup."""
    loglevel = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(level=loglevel, format="%(asctime)s %(message)s")

    print(
        f"[Start of driftas_experiment] Current Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    stream_types = {
        "sudden2": (
            StreamGeneratorSudden,
            {
                "algo_order": ["BF", "FF", "WF", "NF"],
                "nb_train_algo": 2,
                "nb_train_instances": 500,
            },
        ),
        "sudden3": (
            StreamGeneratorSudden,
            {
                "algo_order": ["BF", "FF", "WF", "NF"],
                "nb_train_algo": 3,
                "nb_train_instances": 500,
            },
        ),
        "recurrent200": (
            StreamGeneratorRecurrent,
            {
                "algo_train": ["BF", "FF"],
                "algo_analysis": ["WF", "NF"],
                "nb_train_instances": 500,
                "length_drift": 200,
                "nb_drift_occurences": 3,
                "nb_instance_gap_drift": 300,
            },
        ),
        "recurrent50": (
            StreamGeneratorRecurrent,
            {
                "algo_train": ["BF", "FF"],
                "algo_analysis": ["WF", "NF"],
                "nb_train_instances": 500,
                "length_drift": 50,
                "nb_drift_occurences": 3,
                "nb_instance_gap_drift": 300,
            },
        ),
        "smoothBFFF": (
            StreamGeneratorSmooth,
            {"algo_train": ["BF", "FF"], "stream_length": 4000},
        ),
        "smoothWFFF": (
            StreamGeneratorSmooth,
            {"algo_train": ["WF", "FF"], "stream_length": 4000},
        ),
    }

    stream_seeds = list(range(50))

    selectors = {
        "random": StreamAS(additional_runs=0, retrain_policy=None),
        "random2": StreamAS(
            additional_runs=0,
            retrain_policy=None,
            start_selector=RandomSelector(["BF", "FF", "WF", "NF"], size=2),
        ),
        "fixedselector": FixedSelector(train_period=500),
        "fixedretrain50": StreamAS(additional_runs=1, retrain_policy=50),
        "driftguided": StreamAS(
            additional_runs=1, retrain_policy="drift", train_period=500
        ),
        "driftguidedcostbased": StreamAS(
            additional_runs=1,
            retrain_policy="drift",
            additional_strategy="cost_based",
            train_period=500,
        ),
        "mab": MABSelector(train_period=500, selector_runs=2, additional_runs=0),
        "mabretrain50": MABSelector(
            train_period=500, retrain_policy=50, selector_runs=2, additional_runs=0
        ),
        "mabdriftguided": MABSelector(
            train_period=500, retrain_policy="drift", selector_runs=2, additional_runs=0
        ),
        "mabsinglerun": MABSelector(
            train_period=500, selector_runs=1, additional_runs=0
        ),
        "mab+additional": MABSelector(
            train_period=500, retrain_policy=50, selector_runs=1, additional_runs=1
        ),
    }

    exp_space = {
        "stream_types": stream_types,
        "stream_seeds": stream_seeds,
        "selectors": selectors,
    }

    def run_pipeline(experiment, expclass: Experiment):
        stream_class = experiment["stream_types"][0]
        stream_generate_kwargs = experiment["stream_types"][1]
        stream = stream_class("Data/BP_selected_features.csv")
        seed = experiment["stream_seeds"]
        selector = experiment["selectors"]
        selector.portfolio = stream.get_algorithms()
        selector.feature_extractor = stream.get_features
        selector.target_algorithm = stream.get_performance
        selector.initialize()

        stream.generate(seed, **stream_generate_kwargs)
        drift_dict = dict(
            zip(stream.instance_order, stream.generate_drift_detection(500, 50))
        )

        # Scenario
        for instance in tqdm(stream.instance_order):
            selector(instance)

        return {"stream": stream, "selector": selector, "drift_detection": drift_dict}

    actions = {"simulate": Action("simulate", run_pipeline)}

    print(f"[Experiment loaded] Current Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    Experiment(exp_space, actions)


if __name__ == "__main__":
    main()
