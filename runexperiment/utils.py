from typing import Tuple
import os
import subprocess

__all__ = ["get_cpus", "run_local_worker"]


def get_cpus() -> int:
    """
    Get the number of CPUs per task in a SLURM job or fallback to local CPU count.
    """
    cpus_per_task = os.getenv("SLURM_CPUS_PER_TASK")
    if cpus_per_task is not None:
        return int(cpus_per_task)
    return os.cpu_count() or 1


def run_local_worker(command: str) -> Tuple[int, str, str]:
    """
    Run a shell command and capture return code, stdout and stderr.
    """
    print(command)
    process = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )
    return process.returncode, process.stdout, process.stderr
