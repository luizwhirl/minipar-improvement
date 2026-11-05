"""Allocate a private artifact directory for each compiler invocation."""
import os
import tempfile


def create_run_dir(output_root="output") -> str:
    runs_dir = os.path.abspath(os.path.join(output_root, "runs"))
    os.makedirs(runs_dir, exist_ok=True)
    return tempfile.mkdtemp(prefix="run-", dir=runs_dir)


def executable_path(output_dir: str, output_name: str) -> str:
    extension = ".exe" if os.name == "nt" else ""
    return os.path.join(output_dir, output_name + extension)
