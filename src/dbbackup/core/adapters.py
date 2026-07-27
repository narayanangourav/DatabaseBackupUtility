from __future__ import annotations

import gzip
import os
import shutil
import sqlite3
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from ..exceptions import BackupError
from ..models.backup import ConnectionOptions, RestoreOptions

PASSWORD_ENV = "DBBACKUP_PASSWORD"


def _require_tool(tool: str) -> None:
    if shutil.which(tool) is None:
        raise BackupError(f"Required executable '{tool}' was not found on PATH.")


def _run(command: list[str], input_stream: object | None = None, output_stream: object | None = None, password: str | None = None) -> None:
    environment = os.environ.copy()
    connection_password = password or environment.get(PASSWORD_ENV)
    if connection_password:
        if command[0].startswith("mysql"):
            environment["MYSQL_PWD"] = connection_password
        elif command[0].startswith("pg_") or command[0] in {"pg_dump", "pg_restore", "psql"}:
            environment["PGPASSWORD"] = connection_password
    result = subprocess.run(command, stdin=input_stream, stdout=output_stream, env=environment, check=False)
    if result.returncode != 0:
        raise BackupError(f"Native command failed with exit code {result.returncode}: {command[0]}")


class DatabaseAdapter(ABC):
    engine: str

    def validate_backup_type(self, backup_type: str) -> None:
        if backup_type != "full":
            raise BackupError(f"{self.engine} adapter safely supports full backups only.")

    @abstractmethod
    def test_connection(self, connection: ConnectionOptions) -> None: ...

    @abstractmethod
    def backup(self, connection: ConnectionOptions, destination: Path) -> None: ...

    @abstractmethod
    def restore(self, options: RestoreOptions) -> None: ...


class SQLiteAdapter(DatabaseAdapter):
    engine = "sqlite"

    def test_connection(self, connection: ConnectionOptions) -> None:
        source = Path(connection.database)
        if not source.is_file():
            raise BackupError(f"SQLite database does not exist: {source}")
        try:
            database = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
            try:
                database.execute("PRAGMA schema_version").fetchone()
            finally:
                database.close()
        except sqlite3.Error as error:
            raise BackupError(f"Cannot connect to SQLite database: {error}") from error

    def backup(self, connection: ConnectionOptions, destination: Path) -> None:
        self.test_connection(connection)
        try:
            source = sqlite3.connect(connection.database)
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        except sqlite3.Error as error:
            raise BackupError(f"SQLite backup failed: {error}") from error

    def restore(self, options: RestoreOptions) -> None:
        if options.tables:
            raise BackupError("Selective SQLite restore is not supported by this safe file-level adapter.")
        try:
            source = sqlite3.connect(options.archive)
            target = sqlite3.connect(options.connection.database)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        except sqlite3.Error as error:
            raise BackupError(f"SQLite restore failed: {error}") from error


class NativeAdapter(DatabaseAdapter):
    dump_tool: str
    test_command: list[str]

    def _base_connection_args(self, connection: ConnectionOptions) -> list[str]:
        return []

    def test_connection(self, connection: ConnectionOptions) -> None:
        _require_tool(self.test_command[0])
        _run(self.test_command + self._base_connection_args(connection), password=connection.password)


class MySQLAdapter(NativeAdapter):
    engine, dump_tool, test_command = "mysql", "mysqldump", ["mysqladmin", "ping"]

    def _base_connection_args(self, c: ConnectionOptions) -> list[str]:
        arguments = []
        if c.host: arguments += ["--host", c.host]
        if c.port: arguments += ["--port", str(c.port)]
        if c.user: arguments += ["--user", c.user]
        return arguments

    def backup(self, c: ConnectionOptions, destination: Path) -> None:
        _require_tool(self.dump_tool)
        with destination.open("wb") as output:
            _run([self.dump_tool, "--single-transaction", "--routines", "--events", *self._base_connection_args(c), c.database], output_stream=output, password=c.password)

    def restore(self, options: RestoreOptions) -> None:
        _require_tool("mysql")
        with options.archive.open("rb") as source:
            _run(["mysql", *self._base_connection_args(options.connection), options.connection.database], source, password=options.connection.password)


class PostgresAdapter(NativeAdapter):
    engine, dump_tool, test_command = "postgres", "pg_dump", ["pg_isready"]

    def _base_connection_args(self, c: ConnectionOptions) -> list[str]:
        arguments = ["--dbname", c.database]
        if c.host: arguments += ["--host", c.host]
        if c.port: arguments += ["--port", str(c.port)]
        if c.user: arguments += ["--username", c.user]
        return arguments

    def test_connection(self, c: ConnectionOptions) -> None:
        _require_tool("pg_isready")
        _run(["pg_isready", *self._base_connection_args(c)], password=c.password)

    def backup(self, c: ConnectionOptions, destination: Path) -> None:
        _require_tool(self.dump_tool)
        with destination.open("wb") as output:
            _run([self.dump_tool, "--format=custom", *self._base_connection_args(c)], output_stream=output, password=c.password)

    def restore(self, options: RestoreOptions) -> None:
        _require_tool("pg_restore")
        command = ["pg_restore", "--clean", "--if-exists", "--no-owner", *self._base_connection_args(options.connection)]
        for table in options.tables: command += ["--table", table]
        with options.archive.open("rb") as source:
            _run(command, source, password=options.connection.password)


class MongoAdapter(NativeAdapter):
    engine, dump_tool, test_command = "mongodb", "mongodump", ["mongosh", "--quiet", "--eval", "db.runCommand({ping:1})"]

    def _uri(self, c: ConnectionOptions) -> str:
        authentication = f"{c.user}:{c.password}@" if c.user and c.password else ""
        host = c.host or "localhost"
        port = f":{c.port}" if c.port else ""
        return f"mongodb://{authentication}{host}{port}/{c.database}"

    def test_connection(self, c: ConnectionOptions) -> None:
        _require_tool("mongosh")
        _run(["mongosh", self._uri(c), "--quiet", "--eval", "db.runCommand({ping:1})"])

    def backup(self, c: ConnectionOptions, destination: Path) -> None:
        _require_tool(self.dump_tool)
        _run([self.dump_tool, "--uri", self._uri(c), "--archive", str(destination)])

    def restore(self, options: RestoreOptions) -> None:
        _require_tool("mongorestore")
        command = ["mongorestore", "--uri", self._uri(options.connection), "--archive", str(options.archive)]
        for table in options.tables: command += ["--nsInclude", f"{options.connection.database}.{table}"]
        _run(command)


ADAPTERS: dict[str, DatabaseAdapter] = {adapter.engine: adapter for adapter in (SQLiteAdapter(), MySQLAdapter(), PostgresAdapter(), MongoAdapter())}


def get_adapter(engine: str) -> DatabaseAdapter:
    normalized = {"postgresql": "postgres", "mongo": "mongodb", "mariadb": "mysql"}.get(engine.lower(), engine.lower())
    adapter = ADAPTERS.get(normalized)
    if adapter is None:
        raise BackupError(f"Unsupported engine '{engine}'. Supported engines: {', '.join(ADAPTERS)}.")
    return adapter


def gzip_file(source: Path, destination: Path) -> None:
    with source.open("rb") as raw, gzip.open(destination, "wb") as compressed:
        shutil.copyfileobj(raw, compressed, length=1024 * 1024)


def gunzip_file(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as compressed, destination.open("wb") as raw:
        shutil.copyfileobj(compressed, raw, length=1024 * 1024)
