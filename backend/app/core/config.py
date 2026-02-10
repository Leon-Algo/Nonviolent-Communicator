from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self.database_url


settings = Settings()
