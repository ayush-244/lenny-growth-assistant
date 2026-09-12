from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Application
    app_env: str = "development"

    # PostgreSQL
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "lenny"
    postgres_user: str = "lenny"
    postgres_password: str = "lenny"

    # Model provider
    model_provider: str = "ollama"

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"

    # Anthropic
    anthropic_api_key: str = ""

    # Embeddings
    embedding_provider: str = "local"
    embedding_model: str = ""
    embedding_dimension: str = ""

    @property
    def database_url(self) -> str:
        """Build the PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
