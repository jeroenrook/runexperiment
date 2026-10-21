import sys
from types import SimpleNamespace

import runexperiment.experiment as experiment_module
from runexperiment.action import Action
from runexperiment.experiment import Experiment


def _experiment(tmp_path, **arg_overrides):
    exp = Experiment.__new__(Experiment)
    exp.experiment_space = {"foo": ["a", "b"]}
    exp.action_space = {"act": Action("act", lambda *_args, **_kwargs: None)}
    exp._invocation = "python -m runexperiment"
    args = dict(
        action="act",
        name="demo",
        expdir=tmp_path / "output",
        targetdir=tmp_path / "results",
        config=str(tmp_path / "config.yaml"),
        modus="launch",
        runlocal=False,
        dummy=True,
        replace=False,
        repair=False,
        sbatch_args=[],
        sbatch_array_limit=None,
        sbatch_commands_per_task=1,
        foo=["a", "b"],
    )
    args.update(arg_overrides)
    exp.args = SimpleNamespace(**args)
    return exp


def _construct(monkeypatch, tmp_path, argv, config=None):
    """Run the real constructor (argument parsing included) in tmp_path,
    recording the launch instead of performing it."""
    monkeypatch.chdir(tmp_path)
    if config is not None:
        (tmp_path / "config.yaml").write_text(config)
    monkeypatch.setattr(sys, "argv", ["experiment.py", *argv])
    launched = []
    monkeypatch.setattr(Experiment, "launch", lambda self: launched.append(1))
    space = {"foo": ["a", "b"]}
    actions = {"act": Action("act", lambda *_args, **_kwargs: None)}
    exp = Experiment(space, actions)
    assert launched == [1]
    return exp


def test_invocation_flag_overrides_detected_invocation(monkeypatch, tmp_path):
    command = "apptainer exec image.sif python /abs/experiment.py"
    exp = _construct(monkeypatch, tmp_path, ["launch", "--invocation", command])
    assert exp._invocation == command


def test_invocation_and_submit_are_read_from_config(monkeypatch, tmp_path):
    config = 'invocation: "apptainer exec image.sif python x.py"\n'
    config += "submit: false\n"
    exp = _construct(monkeypatch, tmp_path, ["launch"], config=config)
    assert exp._invocation == "apptainer exec image.sif python x.py"
    assert exp.args.submit is False


def test_without_invocation_the_detected_one_is_kept(monkeypatch, tmp_path):
    exp = _construct(monkeypatch, tmp_path, ["launch"])
    assert exp._invocation == exp._detect_invocation()
    assert exp.args.submit is None


def test_run_commands_use_the_invocation(capsys, tmp_path):
    exp = _experiment(tmp_path, dummy=False)
    exp._invocation = "apptainer exec image.sif python /abs/experiment.py"
    exp.launch()
    out = capsys.readouterr().out
    assert "    apptainer exec image.sif python /abs/experiment.py" in out


def test_no_submit_writes_scripts_without_sbatch(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    # sbatch is unavailable (e.g. inside a container): no local-run prompt.
    monkeypatch.setattr(experiment_module.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: (_ for _ in ()).throw(AssertionError("prompted")),
    )
    submitted = []
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: submitted.append(a))

    _experiment(tmp_path, submit=False).launch()

    scripts = list(tmp_path.glob("launch_*_0.sh"))
    assert len(scripts) == 1
    assert submitted == []
    out = capsys.readouterr().out
    assert f"Submit with: sbatch {scripts[0].resolve()}" in out


def test_submit_by_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(experiment_module.shutil, "which", lambda _: "sbatch")
    submitted = []
    monkeypatch.setattr("subprocess.run", lambda cmd, *a, **kw: submitted.append(cmd))

    _experiment(tmp_path).launch()

    assert len(submitted) == 1 and submitted[0][0] == "sbatch"
