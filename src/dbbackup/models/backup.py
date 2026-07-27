from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

BackupType = Literal["full", "incremental", "differential"]


@dataclass(frozen=True)
class ConnectionOptions:
    engine: str
    database: str
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None


@dataclass(frozen=True)
class BackupOptions:
    connection: ConnectionOptions
    output_directory: Path
    backup_type: BackupType
    custom_backup_command: str | None = None
    custom_restore_command: str | None = None


@dataclass(frozen=True)
class RestoreOptions:
    connection: ConnectionOptions
    archive: Path
    tables: tuple[str, ...] = ()
    custom_restore_command: str | None = None
