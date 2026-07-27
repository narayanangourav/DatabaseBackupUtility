from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from ..core.adapters import get_adapter, gunzip_file, gzip_file
from ..core.storage import store_file
from ..exceptions import BackupError
from ..models.backup import BackupOptions, RestoreOptions

LOGGER = logging.getLogger("dbbackup")


def configure_logging(log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers, force=True)


def _archive_name(database: str, engine: str) -> str:
    safe_name = "".join(character if character.isalnum() or character in "-_" else "_" for character in Path(database).stem)
    return f"{safe_name}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.{engine}.gz"


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _notify(webhook: str | None, message: str) -> None:
    if not webhook:
        return
    request = urllib.request.Request(webhook, data=json.dumps({"text": message}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 300:
                LOGGER.warning("Slack notification returned status %s", response.status)
    except OSError as error:
        LOGGER.warning("Slack notification failed: %s", error)


def backup(options: BackupOptions, storage: str | None, slack_webhook: str | None) -> Path:
    started = time.monotonic()
    adapter = get_adapter(options.connection.engine)
    adapter.validate_backup_type(options.backup_type)
    options.output_directory.mkdir(parents=True, exist_ok=True)
    archive = options.output_directory / _archive_name(options.connection.database, adapter.engine)
    with tempfile.TemporaryDirectory(dir=options.output_directory) as temporary_directory:
        raw_backup = Path(temporary_directory) / "database.backup"
        try:
            LOGGER.info("Starting %s backup for %s", options.backup_type, adapter.engine)
            adapter.test_connection(options.connection)
            adapter.backup(options.connection, raw_backup)
            gzip_file(raw_backup, archive)
            manifest = {
                "engine": adapter.engine,
                "database": options.connection.database,
                "backup_type": options.backup_type,
                "created_at": datetime.now(UTC).isoformat(),
                "archive": archive.name,
                "sha256": _checksum(archive),
                "size_bytes": archive.stat().st_size,
            }
            manifest_path = archive.with_suffix(archive.suffix + ".json")
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            if storage:
                location = store_file(archive, storage)
                store_file(manifest_path, storage)
            else:
                location = str(archive)
            LOGGER.info("Backup completed in %.2fs: %s", time.monotonic() - started, location)
            _notify(slack_webhook, f"Database backup succeeded: {archive.name}")
            return archive
        except (BackupError, OSError) as error:
            LOGGER.exception("Backup failed after %.2fs", time.monotonic() - started)
            _notify(slack_webhook, f"Database backup failed: {adapter.engine}")
            if archive.exists():
                archive.unlink()
            raise BackupError(str(error)) from error


def restore(options: RestoreOptions) -> None:
    adapter = get_adapter(options.connection.engine)
    if not options.archive.is_file():
        raise BackupError(f"Backup archive does not exist: {options.archive}")
    with tempfile.TemporaryDirectory() as temporary_directory:
        raw_backup = Path(temporary_directory) / "database.backup"
        try:
            gunzip_file(options.archive, raw_backup)
            adapter.restore(RestoreOptions(options.connection, raw_backup, options.tables, options.custom_restore_command))
            LOGGER.info("Restore completed from %s", options.archive)
        except (BackupError, OSError) as error:
            LOGGER.exception("Restore failed")
            raise BackupError(str(error)) from error
