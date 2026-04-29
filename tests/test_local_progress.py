from types import SimpleNamespace

import runexperiment.experiment as experiment_module
from runexperiment.action import Action
from runexperiment.experiment import Experiment


def test_launch_local_shows_progress_bar(monkeypatch, tmp_path):
    commands_seen = {}

    class FakePool:
        def __init__(self, processes):
            commands_seen["processes"] = processes

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def imap_unordered(self, func, iterable):
            commands_seen["commands"] = list(iterable)
            for cmd in commands_seen["commands"]:
                yield ("ok", "", "")

    monkeypatch.setattr(experiment_module.mp, "Pool", FakePool)
    monkeypatch.setattr(experiment_module, "get_cpus", lambda: 4)

    tqdm_calls = {}

    def fake_tqdm(iterable, total=None, desc=None):
        tqdm_calls["total"] = total
        tqdm_calls["desc"] = desc
        tqdm_calls["items"] = list(iterable)
        return tqdm_calls["items"]

    monkeypatch.setattr(experiment_module, "tqdm", fake_tqdm)

    exp = Experiment.__new__(Experiment)
    exp.experiment_space = {"foo": ["bar"]}
    exp.action_space = {"act": Action("act", lambda *_args, **_kwargs: None)}
    exp._invocation = "python -m runexperiment"

    args = SimpleNamespace(
        action="act",
        name="demo",
        expdir=tmp_path / "output",
        targetdir=tmp_path / "results",
        config=str(tmp_path / "config.yaml"),
        modus="launch",
        runlocal=True,
        dummy=True,
        replace=False,
        repair=False,
        sbatch_args=[],
        sbatch_array_limit=None,
        foo=["bar"],
    )
    exp.args = args

    exp.launch()

    expected_command = (
        f"{exp._invocation} --action act --name demo"
        f" --expdir {args.expdir}"
        f" --targetdir {args.targetdir}"
        f" --config {args.config}"
        f" run --foo bar"
    )
    assert commands_seen["commands"] == [expected_command]
    assert commands_seen["processes"] == 3
    assert tqdm_calls["total"] == 1
    assert tqdm_calls["desc"] == "Running locally"
