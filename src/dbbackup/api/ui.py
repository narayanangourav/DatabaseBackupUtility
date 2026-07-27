from __future__ import annotations

from types import ModuleType

from ..exceptions import BackupError
from ..services.ui_service import run_backup, run_restore

ENGINES = ["sqlite", "mysql", "postgres", "mongodb"]
BACKUP_TYPES = ["full"]
UI_CSS = """
textarea { overflow-y: hidden !important; resize: none !important; }
.required-indicator { color: #dc2626; font-weight: 700; }
.field-label { margin-bottom: -8px; }
footer { display: none !important; }
nav { display: none !important; }
header { display: none !important; }
"""


def _backup_result(engine: str, database: str, host: str, port: str, user: str, password: str, output_directory: str, backup_type: str, storage: str, slack_webhook: str) -> str:
    try:
        return run_backup(engine, database, host, port, user, password, output_directory, backup_type, storage, slack_webhook)
    except BackupError as error:
        return f"Backup failed: {error}"


def _restore_result(engine: str, database: str, host: str, port: str, user: str, password: str, archive: str, tables: str) -> str:
    try:
        return run_restore(engine, database, host, port, user, password, archive, tables)
    except BackupError as error:
        return f"Restore failed: {error}"


def _field_label(gradio: ModuleType, label: str, required: bool = False) -> None:
    marker = ' <span class="required-indicator" aria-label="required">*</span>' if required else ""
    gradio.HTML(f"<div>{label}{marker}</div>", elem_classes=["field-label"])


def _build_backup_page(gradio: ModuleType) -> None:
    with gradio.Row():
        with gradio.Column():
            _field_label(gradio, "Database Engine", required=True)
            backup_engine = gradio.Dropdown(ENGINES, value="sqlite", show_label=False)
        with gradio.Column():
            _field_label(gradio, "Database Name or SQLite File Path", required=True)
            backup_database = gradio.Textbox(placeholder="C:\\data\\app.db or my_database", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Host")
            backup_host = gradio.Textbox(placeholder="localhost or db.example.com", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Port")
            backup_port = gradio.Textbox(placeholder="5432 for PostgreSQL; leave blank for SQLite", lines=1, max_lines=1, show_label=False)
    with gradio.Row():
        with gradio.Column():
            _field_label(gradio, "Username")
            backup_user = gradio.Textbox(placeholder="postgres, root, or database user", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Password")
            backup_password = gradio.Textbox(placeholder="Leave blank to use environment credentials", type="password", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Backup Type", required=True)
            backup_type = gradio.Dropdown(BACKUP_TYPES, value="full", show_label=False)
    with gradio.Row():
        with gradio.Column():
            _field_label(gradio, "Local Output Directory", required=True)
            backup_output = gradio.Textbox(placeholder="C:\\backups", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Optional Storage Target (Local Path, S3://, GS://, AZ://)")
            backup_storage = gradio.Textbox(placeholder="s3://company-backups/production", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Optional Slack Webhook")
            backup_slack = gradio.Textbox(placeholder="https://hooks.slack.com/services/...", type="password", lines=1, max_lines=1, show_label=False)
    backup_button = gradio.Button("Create Backup", variant="primary")
    backup_status = gradio.Textbox(label="Status")
    backup_button.click(_backup_result, [backup_engine, backup_database, backup_host, backup_port, backup_user, backup_password, backup_output, backup_type, backup_storage, backup_slack], backup_status)


def _build_restore_page(gradio: ModuleType) -> None:
    with gradio.Row():
        with gradio.Column():
            _field_label(gradio, "Database Engine", required=True)
            restore_engine = gradio.Dropdown(ENGINES, value="sqlite", show_label=False)
        with gradio.Column():
            _field_label(gradio, "Database Name or SQLite File Path", required=True)
            restore_database = gradio.Textbox(placeholder="C:\\data\\restored.db or my_database", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Host")
            restore_host = gradio.Textbox(placeholder="localhost or db.example.com", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Port")
            restore_port = gradio.Textbox(placeholder="5432 for PostgreSQL; leave blank for SQLite", lines=1, max_lines=1, show_label=False)
    with gradio.Row():
        with gradio.Column():
            _field_label(gradio, "Username")
            restore_user = gradio.Textbox(placeholder="postgres, root, or database user", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Password")
            restore_password = gradio.Textbox(placeholder="Leave blank to use environment credentials", type="password", lines=1, max_lines=1, show_label=False)
    with gradio.Row():
        with gradio.Column():
            _field_label(gradio, "Compressed Backup Archive Path", required=True)
            restore_archive = gradio.Textbox(placeholder="C:\\backups\\my_database-20260727T000000Z.postgres.gz", lines=1, max_lines=1, show_label=False)
        with gradio.Column():
            _field_label(gradio, "Optional Tables or Collections (Comma-Separated)")
            restore_tables = gradio.Textbox(placeholder="users, orders, audit_log", lines=1, max_lines=1, show_label=False)
    restore_button = gradio.Button("Restore Backup", variant="primary")
    restore_status = gradio.Textbox(label="Status")
    restore_button.click(_restore_result, [restore_engine, restore_database, restore_host, restore_port, restore_user, restore_password, restore_archive, restore_tables], restore_status)


def _build_tabbed_page(gradio: ModuleType, selected_tab: str) -> None:
    gradio.Markdown("# Database Backup Utility\nCreate, store, and restore compressed database backups.")
    with gradio.Tabs(selected=selected_tab):
        with gradio.Tab("Backup", id="backup") as backup_tab:
            _build_backup_page(gradio)
        with gradio.Tab("Restore", id="restore") as restore_tab:
            _build_restore_page(gradio)
    backup_tab.select(None, js="() => window.location.assign('/backup')", queue=False)
    restore_tab.select(None, js="() => window.location.assign('/restore')", queue=False)


def _create_application(gradio: ModuleType, theme: object, selected_tab: str) -> object:
    with gradio.Blocks(title="Database Backup Utility", theme=theme, css=UI_CSS) as application:
        _build_tabbed_page(gradio, selected_tab)
    return application


def launch_ui(host: str, port: int) -> None:
    try:
        import gradio as gr
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import RedirectResponse
    except ImportError as error:
        raise BackupError("Gradio is not installed. Run: uv sync") from error

    lime_theme_color = gr.themes.Color(
        c50="#f7fee7", c100="#ecfccb", c200="#d9f99d", c300="#bef264", c400="#a3e635", c500="#84cc16",
        c600="#65a30d", c700="#4d7c0f", c800="#3f6212", c900="#365314", c950="#1a2e05", name="dbbackup-lime",
    )
    theme = gr.themes.Citrus(primary_hue=lime_theme_color)
    backup_application = _create_application(gr, theme, "backup")
    restore_application = _create_application(gr, theme, "restore")
    server = FastAPI()

    @server.get("/", include_in_schema=False)
    def redirect_to_backup() -> RedirectResponse:
        return RedirectResponse(url="/backup")

    gr.mount_gradio_app(server, backup_application, path="/backup")
    gr.mount_gradio_app(server, restore_application, path="/restore")
    uvicorn.run(server, host=host, port=port)
