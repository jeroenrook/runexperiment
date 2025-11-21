import sys
from types import ModuleType

from runexperiment.experiment import Experiment


def test_detect_invocation_uses_main_file(monkeypatch, tmp_path):
    main_mod = ModuleType("__main__")
    dummy = tmp_path / "dummy_script.py"
    dummy.write_text("print('hi')")
    main_mod.__file__ = str(dummy)
    monkeypatch.setitem(sys.modules, "__main__", main_mod)

    exp = Experiment.__new__(Experiment)
    invocation = Experiment._detect_invocation(exp)
    assert str(dummy) in invocation
    assert sys.executable in invocation


def test_detect_invocation_fallback_module(monkeypatch):
    main_mod = ModuleType("__main__")
    if hasattr(main_mod, "__file__"):
        delattr(main_mod, "__file__")
    monkeypatch.setitem(sys.modules, "__main__", main_mod)

    exp = Experiment.__new__(Experiment)
    invocation = Experiment._detect_invocation(exp)
    assert "-m runexperiment" in invocation
