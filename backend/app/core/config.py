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

    # Model provider (used for conversation generation)
    model_provider: str = "ollama"

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"

    # LLM request timeout in seconds
    llm_timeout: float = 120.0

    # Embeddings (Phase 2 — unchanged)
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768

    # RAG retrieval (Phase 2 — unchanged)
    rag_top_k: int = 5
    rag_min_similarity: float = 0.35

    # Conversation window: number of recent messages to load per turn
    # 10 messages = 5 conversation turns (user + assistant pairs)
    conversation_window: int = 10

    @property
    def database_url(self) -> str:
        """Build the PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
