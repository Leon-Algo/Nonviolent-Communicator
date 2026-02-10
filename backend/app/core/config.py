from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    mock_auth_enabled: bool = Field(default=True, alias="MOCK_AUTH_ENABLED")

    database_url: str = Field(alias="DATABASE_URL")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: str | None = Field(
        default=None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )

    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(
        default="Qwen/Qwen3-Coder-480B-A35B-Instruct", alias="LLM_MODEL"
    )
    openai_base_url: str = Field(
        default="https://api-inference.modelscope.cn/v1", alias="OPENAI_BASE_URL"
    )
    anthropic_base_url: str = Field(
        default="https://api-inference.modelscope.cn", alias="ANTHROPIC_BASE_URL"
    )
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    cors_origin_regex: str = Field(
        default=r"https://.*\.vercel\.app", alias="CORS_ORIGIN_REGEX"
    )

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(ROOT_DIR / ".env")),
        env_file_encoding="utf-8",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        db_url = self.database_url.strip()
        if db_url.startswith("postgresql+asyncpg://"):
            return db_url
        if db_url.startswith("postgresql://"):
            return db_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return db_url

    @field_validator(
        "app_env",
        "log_level",
        "database_url",
        "supabase_url",
        "supabase_service_role_key",
        "llm_api_key",
        "llm_model",
        "openai_base_url",
        "anthropic_base_url",
        "cors_origins",
        "cors_origin_regex",
        mode="before",
    )
    @classmethod
    def strip_string_values(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("mock_auth_enabled", mode="before")
    @classmethod
    def parse_mock_auth_enabled(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return value


settings = Settings()
