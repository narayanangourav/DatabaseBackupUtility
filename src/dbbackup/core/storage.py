from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..exceptions import BackupError


def store_file(source: Path, target: str) -> str:
    if target.startswith("s3://"):
        command = ["aws", "s3", "cp", str(source), target.rstrip("/") + "/" + source.name]
    elif target.startswith("gs://"):
        command = ["gcloud", "storage", "cp", str(source), target.rstrip("/") + "/" + source.name]
    elif target.startswith("az://"):
        container, _, prefix = target.removeprefix("az://").partition("/")
        command = ["az", "storage", "blob", "upload", "--container-name", container, "--name", f"{prefix.rstrip('/')}/{source.name}", "--file", str(source), "--overwrite", "false"]
    else:
        destination = Path(target)
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination / source.name)
        return str(destination / source.name)
    if shutil.which(command[0]) is None:
        raise BackupError(f"Storage CLI '{command[0]}' was not found on PATH.")
    if subprocess.run(command, check=False).returncode != 0:
        raise BackupError(f"Could not upload backup using {command[0]}.")
    return target.rstrip("/") + "/" + source.name
