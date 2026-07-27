import sqlite3
import tempfile
import unittest
from pathlib import Path

from dbbackup.models import BackupOptions, ConnectionOptions, RestoreOptions
from dbbackup.services.backup_service import backup, configure_logging, restore


class SQLiteBackupTests(unittest.TestCase):
    def test_backup_and_restore_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.db"
            database = sqlite3.connect(source)
            try:
                database.execute("CREATE TABLE messages (body TEXT)")
                database.execute("INSERT INTO messages VALUES ('hello')")
                database.commit()
            finally:
                database.close()
            configure_logging(None)
            connection = ConnectionOptions("sqlite", str(source))
            archive = backup(BackupOptions(connection, root / "backups", "full"), None, None)
            target = root / "target.db"
            restore(RestoreOptions(ConnectionOptions("sqlite", str(target)), archive))
            database = sqlite3.connect(target)
            try:
                self.assertEqual(database.execute("SELECT body FROM messages").fetchone()[0], "hello")
            finally:
                database.close()

    def test_incremental_sqlite_backup_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.db"
            sqlite3.connect(source).close()
            with self.assertRaisesRegex(Exception, "full backups only"):
                backup(BackupOptions(ConnectionOptions("sqlite", str(source)), Path(directory), "incremental"), None, None)
