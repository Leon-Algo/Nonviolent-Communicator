from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    slow_request_ms: int = Field(default=1200, alias="SLOW_REQUEST_MS")
    observability_recent_error_limit: int = Field(
        default=20, alias="OBSERVABILITY_RECENT_ERROR_LIMIT"
    )
    auth_mode: str = Field(default="mock", alias="AUTH_MODE")
    mock_auth_enabled: bool = Field(default=True, alias="MOCK_AUTH_ENABLED")
    allow_mock_auth_in_production: bool = Field(
        default=False, alias="ALLOW_MOCK_AUTH_IN_PRODUCTION"
    )

    database_url: str = Field(alias="DATABASE_URL")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = Field(
        default=None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    jwt_audience: str = Field(default="authenticated", alias="JWT_AUDIENCE")
    jwt_issuer: str | None = Field(default=None, alias="JWT_ISSUER")

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
        extra="ignore",
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
        "slow_request_ms",
        "observability_recent_error_limit",
        "auth_mode",
        "database_url",
        "supabase_url",
        "supabase_anon_key",
        "supabase_service_role_key",
        "jwt_audience",
        "jwt_issuer",
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

    @field_validator("auth_mode", mode="before")
    @classmethod
    def normalize_auth_mode(cls, value):
        if not isinstance(value, str):
            return "mock"
        normalized = value.strip().lower()
        if normalized not in {"mock", "supabase"}:
            return "mock"
        return normalized

    @field_validator("slow_request_ms", mode="before")
    @classmethod
    def normalize_slow_request_ms(cls, value):
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return 1200
        return max(1, normalized)

    @field_validator("observability_recent_error_limit", mode="before")
    @classmethod
    def normalize_recent_error_limit(cls, value):
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return 20
        return max(1, normalized)

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

    @field_validator("allow_mock_auth_in_production", mode="before")
    @classmethod
    def parse_allow_mock_auth_in_production(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return value

    @model_validator(mode="after")
    def enforce_prod_auth_constraints(self):
        if (
            self.app_env.lower() == "production"
            and self.mock_auth_enabled
            and not self.allow_mock_auth_in_production
        ):
            raise ValueError(
                "MOCK_AUTH_ENABLED must be false in production "
                "(or set ALLOW_MOCK_AUTH_IN_PRODUCTION=true for emergency override)"
            )
        return self


settings = Settings()
