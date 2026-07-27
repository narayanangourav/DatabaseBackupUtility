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

Install the project with uv, then prefix commands with `uv run`:

```powershell
uv sync --group dev
uv run dbbackup --help
```

```powershell
uv run dbbackup backup --engine sqlite --database C:\data\app.db --output .\backups
uv run dbbackup restore --engine sqlite --database C:\data\restored.db --file .\backups\app-20260727T120000Z.sqlite.gz
uv run dbbackup test --engine postgres --host localhost --port 5432 --user app --database app
uv run dbbackup schedule --every-minutes 60 -- engine=sqlite database=C:\data\app.db output=.\backups
```

## Web interface

Install the optional UI package and launch the local Gradio interface:

```powershell
uv sync
uv run dbbackup serve
```

Open `http://127.0.0.1:7575/backup` to create backups or `http://127.0.0.1:7575/restore` to restore them. Use `--host 0.0.0.0` only when the host is protected by appropriate network access controls.

The Gradio presentation code lives in `dbbackup/ui/`; backup and restore operations remain in the reusable service layer.

## Container deployment

Build and run locally with Docker Compose:

```powershell
$env:GHCR_OWNER = "your-github-owner"
docker compose up --build
```

Open `http://127.0.0.1:7575/backup`. Backups saved in `/data/backups` persist in the named `backup-data` volume. The image includes SQLite, MySQL, PostgreSQL, and MongoDB client tools.

To pass secrets to the container, set them in the deployment environment rather than committing them:

```powershell
$env:DBBACKUP_PASSWORD = "database-password"
$env:DBBACKUP_SLACK_WEBHOOK = "https://hooks.slack.com/services/..."
docker compose up --build
```

## GitHub deployment

The `CI` workflow runs tests first, builds the Python wheel and source distribution with `uv build`, builds the container only after the package build passes, and then publishes `ghcr.io/OWNER/REPOSITORY` only after the container build passes. Publishing runs for pushes to `master`, version tags, and manual dispatches; pull requests test and build without publishing. It uses the repository-provided `GITHUB_TOKEN`; no repository secret is required. After the first successful run, open the package in the GitHub account or organization **Packages** page and set **Package settings → Change visibility → Public**. The workflow includes the source and MIT license image labels so GitHub can associate the package with this repository. GitHub’s container-publishing guidance documents the required `packages: write` permission and `GITHUB_TOKEN` login. [GitHub Docs](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)

The final `Deploy GitHub Pages` job in the `CI` workflow publishes only the static `docs/` site to GitHub Pages, after tests, package build, Docker build, and GHCR publication succeed. It runs only for `master`. GitHub Pages cannot host this Gradio/Python application or run backups; deploy the GHCR image to a server or container platform for the live application. In repository **Settings → Pages**, select **GitHub Actions** as the build and deployment source. GitHub Pages deployments require `pages: write`, `id-token: write`, and a `github-pages` environment, which the workflow already supplies. [GitHub Pages workflow guidance](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

For the live container host, configure these environment variables through its secret manager or deployment settings:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DBBACKUP_UI_HOST` | Yes | Set to `0.0.0.0` in containers. |
| `DBBACKUP_UI_PORT` | Yes | Set to `7575`. |
| `DBBACKUP_PASSWORD` | When DB authentication requires it | Database password for MySQL/PostgreSQL. |
| `DBBACKUP_SLACK_WEBHOOK` | No | Slack completion notifications. |

Use `uv run dbbackup --help` and `uv run dbbackup backup --help` for all options. A backup type is recorded in the manifest. Full backups work for every adapter; incremental and differential backups are rejected unless an adapter can safely provide them, rather than silently creating an incorrect backup. Additional DBMSs can be added as focused adapters around their supported native dump and restore tools.

## Cloud storage and notifications

Pass `--storage` a local path, `s3://bucket/prefix`, `gs://bucket/prefix`, or `az://container/prefix`. The corresponding `aws`, `gcloud`, or `az` CLI must be installed and authenticated. `--slack-webhook` sends a completion message; put it in `DBBACKUP_SLACK_WEBHOOK` to avoid putting it in shell history.

## Safety and operational notes

- Test restores regularly and use a least-privilege database account.
- Restore overwrites a SQLite destination; other engines apply data using their native restore tool.
- Manifest files include operational metadata but never passwords.
- For production scheduling, invoke the `backup` command from Task Scheduler, cron, or your platform scheduler. The `schedule` command is a simple foreground interval runner.

## Tests

```powershell
uv run pytest
```
