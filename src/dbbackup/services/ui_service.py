from __future__ import annotations

from pathlib import Path

from ..exceptions import BackupError
from ..models.backup import BackupOptions, ConnectionOptions, RestoreOptions
from .backup_service import backup, restore


def _parse_port(port: str) -> int | None:
    value = port.strip()
    if not value:
        return None
    if not value.isdecimal():
        raise BackupError("Port must be a whole number.")
    parsed_port = int(value)
    if not 1 <= parsed_port <= 65535:
        raise BackupError("Port must be between 1 and 65535.")
    return parsed_port


def run_backup(
    engine: str,
    database: str,
    host: str,
    port: str,
    user: str,
    password: str,
    output_directory: str,
    backup_type: str,
    storage: str,
    slack_webhook: str,
) -> str:
    if backup_type not in {"full", "incremental", "differential"}:
        raise BackupError("Choose a valid backup type.")
    if not database.strip() or not output_directory.strip():
        raise BackupError("Database and output directory are required.")
    connection = ConnectionOptions(engine, database.strip(), host.strip() or None, _parse_port(port), user.strip() or None, password or None)
    archive = backup(BackupOptions(connection, Path(output_directory.strip()), backup_type), storage.strip() or None, slack_webhook.strip() or None)
    return f"Backup completed: {archive}"


def run_restore(
    engine: str,
    database: str,
    host: str,
    port: str,
    user: str,
    password: str,
    archive: str,
    tables: str,
) -> str:
    if not database.strip() or not archive.strip():
        raise BackupError("Database and backup archive are required.")
    connection = ConnectionOptions(engine, database.strip(), host.strip() or None, _parse_port(port), user.strip() or None, password or None)
    selected_tables = tuple(item.strip() for item in tables.split(",") if item.strip())
    restore(RestoreOptions(connection, Path(archive.strip()), selected_tables))
    return "Restore completed."
