from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from .config import Settings
from .core.adapters import get_adapter
from .exceptions import BackupError
from .models.backup import BackupOptions, ConnectionOptions, RestoreOptions
from .services.backup_service import backup, configure_logging, restore


def _connection(arguments: argparse.Namespace) -> ConnectionOptions:
    return ConnectionOptions(arguments.engine, arguments.database, arguments.host, arguments.port, arguments.user, os.getenv("DBBACKUP_PASSWORD"))


def _add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--engine", required=True, help="sqlite, mysql, postgres, or mongodb")
    parser.add_argument("--database", required=True)
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--user")


def _build_parser() -> argparse.ArgumentParser:
    settings = Settings()
    parser = argparse.ArgumentParser(prog="dbbackup", description="Stream, compress, store, and restore database backups.")
    parser.add_argument("--log-file", type=Path, help="Optional activity log destination")
    commands = parser.add_subparsers(dest="command", required=True)
    backup_parser = commands.add_parser("backup", help="Create a compressed backup")
    _add_connection_arguments(backup_parser)
    backup_parser.add_argument("--output", type=Path, required=True, help="Local directory for the archive")
    backup_parser.add_argument("--type", choices=("full", "incremental", "differential"), default="full")
    backup_parser.add_argument("--storage", help="Local directory, s3://, gs://, or az:// target")
    backup_parser.add_argument("--slack-webhook", default=os.getenv("DBBACKUP_SLACK_WEBHOOK"))
    restore_parser = commands.add_parser("restore", help="Restore a compressed backup")
    _add_connection_arguments(restore_parser)
    restore_parser.add_argument("--file", type=Path, required=True)
    restore_parser.add_argument("--table", action="append", default=[], help="Repeat for selective restore where supported")
    test_parser = commands.add_parser("test", help="Test database connectivity")
    _add_connection_arguments(test_parser)
    schedule_parser = commands.add_parser("schedule", help="Run a backup command at a fixed foreground interval")
    schedule_parser.add_argument("--every-minutes", type=int, required=True)
    schedule_parser.add_argument("backup_arguments", nargs=argparse.REMAINDER, help="Arguments after -- passed to backup")
    serve_parser = commands.add_parser("serve", help="Launch the Gradio web interface")
    serve_parser.add_argument("--host", default=settings.ui_host)
    serve_parser.add_argument("--port", type=int, default=settings.ui_port)
    return parser


def _run_schedule(arguments: argparse.Namespace) -> int:
    if arguments.every_minutes < 1 or not arguments.backup_arguments:
        raise BackupError("Schedule needs --every-minutes >= 1 and backup arguments after '--'.")
    backup_arguments = list(arguments.backup_arguments)
    if backup_arguments[0] == "--":
        backup_arguments.pop(0)
    while True:
        result = main(["backup", *backup_arguments])
        if result != 0:
            return result
        time.sleep(arguments.every_minutes * 60)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    configure_logging(arguments.log_file)
    try:
        if arguments.command == "test":
            get_adapter(arguments.engine).test_connection(_connection(arguments))
            print("Connection successful.")
        elif arguments.command == "backup":
            archive = backup(BackupOptions(_connection(arguments), arguments.output, arguments.type), arguments.storage, arguments.slack_webhook)
            print(archive)
        elif arguments.command == "restore":
            restore(RestoreOptions(_connection(arguments), arguments.file, tuple(arguments.table)))
        elif arguments.command == "serve":
            from .api import launch_ui
            launch_ui(arguments.host, arguments.port)
        else:
            return _run_schedule(arguments)
        return 0
    except BackupError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
