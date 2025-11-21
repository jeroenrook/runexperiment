import sys

from runexperiment.__main__ import main


def test_cli_init_creates_files(tmp_path, monkeypatch):
    dest = tmp_path / "proj"
    monkeypatch.setattr(sys, "argv", ["runexperiment", "init", "--dest", str(dest)])

    main()

    exp_file = dest / "experiment.py"
    cfg_file = dest / "config.yaml"

    assert exp_file.exists() and cfg_file.exists()
    assert (exp_file.stat().st_mode & 0o111) != 0  # executable bit set
    text = exp_file.read_text()
    assert "Experiment" in text and "Action" in text
