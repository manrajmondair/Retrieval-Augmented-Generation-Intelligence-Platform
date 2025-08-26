from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "changeme"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_max_tokens: int = 500
    openai_timeout: int = 10

    embeddings_provider: str = "openai"
    embeddings_model: str = "text-embedding-3-small"

    vector_store: str = "qdrant"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "docs"
    chroma_persist_dir: str = ".chroma"
    pinecone_api_key: str | None = None
    pinecone_env: str | None = None
    pinecone_index: str = "docs"

    bm25_k1: float = 1.2
    bm25_b: float = 0.75
    bm25_top_k: int = 12

    vector_top_k: int = 12
    hybrid_fusion: str = "rrf"  # rrf|weighted
    hybrid_rrf_k: int = 60
    hybrid_weight_vector: float = 0.6
    hybrid_weight_bm25: float = 0.4

    redis_url: str = "redis://redis:6379/0"
    rate_limit_qps: int = 50
    cache_ttl_sec: int = 120

    prometheus_enabled: bool = True
    otel_enabled: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

