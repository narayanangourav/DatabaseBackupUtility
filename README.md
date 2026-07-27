# Database Backup Utility

`dbbackup` is a cross-platform command-line utility for reliable database backups and restores. It streams native database dump tools directly into gzip archives, records a manifest beside each archive, and can upload completed backups to S3, Google Cloud Storage, or Azure Blob Storage through their official CLIs.

Source code is contained in `src/dbbackup/`, with core adapters, typed models, orchestration services, and the Gradio UI separated into dedicated modules.

## Supported engines

| Engine | Backup/restore tool |
| --- | --- |
| SQLite | Built-in Python SQLite backup API |
| MySQL / MariaDB | `mysqldump` / `mysql` |
| PostgreSQL | `pg_dump` / `pg_restore` or `psql` |
| MongoDB | `mongodump` / `mongorestore` |

Install the relevant native client tool and ensure it is on `PATH`. Set `DBBACKUP_PASSWORD` for MySQL and PostgreSQL, or use the DBMS's own credential mechanism (for example `.pgpass`). MongoDB credentials are supplied by the engine's configured authentication method.

## Quick start

```powershell
python -m dbbackup backup --engine sqlite --database C:\data\app.db --output .\backups
python -m dbbackup restore --engine sqlite --database C:\data\restored.db --file .\backups\app-20260727T120000Z.sqlite.gz
python -m dbbackup test --engine postgres --host localhost --port 5432 --user app --database app
python -m dbbackup schedule --every-minutes 60 -- engine=sqlite database=C:\data\app.db output=.\backups
```

## Web interface

Install the optional UI package and launch the local Gradio interface:

```powershell
python -m pip install -r requirements.txt
python -m dbbackup serve
```

Open `http://127.0.0.1:7860` in a browser. Use `--host 0.0.0.0` only when the host is protected by appropriate network access controls.

The Gradio presentation code lives in `dbbackup/ui/`; backup and restore operations remain in the reusable service layer.

Use `python -m dbbackup --help` and `python -m dbbackup backup --help` for all options. A backup type is recorded in the manifest. Full backups work for every adapter; incremental and differential backups are rejected unless an adapter can safely provide them, rather than silently creating an incorrect backup. Additional DBMSs can be added as focused adapters around their supported native dump and restore tools.

## Cloud storage and notifications

Pass `--storage` a local path, `s3://bucket/prefix`, `gs://bucket/prefix`, or `az://container/prefix`. The corresponding `aws`, `gcloud`, or `az` CLI must be installed and authenticated. `--slack-webhook` sends a completion message; put it in `DBBACKUP_SLACK_WEBHOOK` to avoid putting it in shell history.

## Safety and operational notes

- Test restores regularly and use a least-privilege database account.
- Restore overwrites a SQLite destination; other engines apply data using their native restore tool.
- Manifest files include operational metadata but never passwords.
- For production scheduling, invoke the `backup` command from Task Scheduler, cron, or your platform scheduler. The `schedule` command is a simple foreground interval runner.

## Tests

```powershell
python -m unittest discover -s tests -v
```
