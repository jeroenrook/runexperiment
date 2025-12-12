from types import SimpleNamespace

from runexperiment.action import Action
from runexperiment.experiment import Experiment


def test_launch_batches_multiple_commands_per_task(capsys, tmp_path):
    exp = Experiment.__new__(Experiment)
    exp.experiment_space = {"foo": ["a", "b", "c"]}
    exp.action_space = {"act": Action("act", lambda *_args, **_kwargs: None)}
    exp._invocation = "python -m runexperiment"

    args = SimpleNamespace(
        action="act",
        name="demo",
        expdir=tmp_path / "output",
        targetdir=tmp_path / "results",
        config=str(tmp_path / "config.yaml"),
        modus="launch",
        runlocal=False,
        dummy=False,
        replace=False,
        repair=False,
        sbatch_args=[],
        sbatch_array_limit=None,
        sbatch_commands_per_task=2,
        foo=["a", "b", "c"],
    )
    exp.args = args

    exp.launch()

    out = capsys.readouterr().out
    assert "COMMANDS_PER_TASK=2" in out
    assert "--array=0-1" in out
    assert "${experiment[$cmd_index]}" in out
    assert "--foo a" in out and "--foo c" in out
