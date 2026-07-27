"""Environment-based application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration shared by optional application entry points."""

    ui_host: str = "127.0.0.1"
    ui_port: int = 7860

    model_config = SettingsConfigDict(env_prefix="DBBACKUP_", env_file=".env", extra="ignore")
