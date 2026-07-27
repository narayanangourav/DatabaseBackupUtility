from __future__ import annotations

from ..exceptions import BackupError
from ..services.ui_service import run_backup, run_restore

ENGINES = ["sqlite", "mysql", "postgres", "mongodb"]
BACKUP_TYPES = ["full", "incremental", "differential"]


def _backup_result(engine: str, database: str, host: str, port: float | None, user: str, password: str, output_directory: str, backup_type: str, storage: str, slack_webhook: str) -> str:
    try:
        return run_backup(engine, database, host, port, user, password, output_directory, backup_type, storage, slack_webhook)
    except BackupError as error:
        return f"Backup failed: {error}"


def _restore_result(engine: str, database: str, host: str, port: float | None, user: str, password: str, archive: str, tables: str) -> str:
    try:
        return run_restore(engine, database, host, port, user, password, archive, tables)
    except BackupError as error:
        return f"Restore failed: {error}"


def launch_ui(host: str, port: int) -> None:
    try:
        import gradio as gr
    except ImportError as error:
        raise BackupError("Gradio is not installed. Run: python -m pip install -r requirements.txt") from error

    with gr.Blocks(title="Database Backup Utility") as application:
        gr.Markdown("# Database Backup Utility\nCreate, store, and restore compressed database backups.")
        with gr.Tab("Backup"):
            with gr.Row():
                backup_engine = gr.Dropdown(ENGINES, value="sqlite", label="Database engine")
                backup_database = gr.Textbox(label="Database name or SQLite file path")
                backup_host = gr.Textbox(label="Host")
                backup_port = gr.Number(label="Port", precision=0)
            with gr.Row():
                backup_user = gr.Textbox(label="Username")
                backup_password = gr.Textbox(label="Password", type="password")
                backup_type = gr.Dropdown(BACKUP_TYPES, value="full", label="Backup type")
            backup_output = gr.Textbox(label="Local output directory")
            backup_storage = gr.Textbox(label="Optional storage target (local path, s3://, gs://, az://)")
            backup_slack = gr.Textbox(label="Optional Slack webhook", type="password")
            backup_button = gr.Button("Create backup", variant="primary")
            backup_status = gr.Textbox(label="Status")
            backup_button.click(_backup_result, [backup_engine, backup_database, backup_host, backup_port, backup_user, backup_password, backup_output, backup_type, backup_storage, backup_slack], backup_status)
        with gr.Tab("Restore"):
            with gr.Row():
                restore_engine = gr.Dropdown(ENGINES, value="sqlite", label="Database engine")
                restore_database = gr.Textbox(label="Database name or SQLite file path")
                restore_host = gr.Textbox(label="Host")
                restore_port = gr.Number(label="Port", precision=0)
            with gr.Row():
                restore_user = gr.Textbox(label="Username")
                restore_password = gr.Textbox(label="Password", type="password")
            restore_archive = gr.Textbox(label="Compressed backup archive path")
            restore_tables = gr.Textbox(label="Optional tables or collections (comma-separated)")
            restore_button = gr.Button("Restore backup", variant="primary")
            restore_status = gr.Textbox(label="Status")
            restore_button.click(_restore_result, [restore_engine, restore_database, restore_host, restore_port, restore_user, restore_password, restore_archive, restore_tables], restore_status)
    application.launch(server_name=host, server_port=port)
