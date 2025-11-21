import os

from runexperiment import utils


def test_get_cpus_uses_slurm_env(monkeypatch):
    monkeypatch.setenv("SLURM_CPUS_PER_TASK", "7")
    assert utils.get_cpus() == 7


def test_get_cpus_fallback(monkeypatch):
    monkeypatch.delenv("SLURM_CPUS_PER_TASK", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 5)
    assert utils.get_cpus() == 5


def test_run_local_worker_invokes_subprocess(monkeypatch):
    calls = {}

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, shell, capture_output, text):
        calls["command"] = command
        calls["shell"] = shell
        calls["capture_output"] = capture_output
        calls["text"] = text
        return Result()

    monkeypatch.setattr(utils.subprocess, "run", fake_run)
    rc, out, err = utils.run_local_worker("echo hi")
    assert rc == 0 and out == "ok" and err == ""
    assert calls["command"] == "echo hi"
    assert calls["shell"] and calls["capture_output"] and calls["text"]
