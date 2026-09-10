from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Provider: il mock non ha bisogno di chiavi e permette di far girare
    # l'intero stack in locale e nei test (spec D2/D3).
    llm_provider: str = "mock"           # mock | openrouter
    retrieval_provider: str = "keyword"  # keyword | qdrant
    kb_path: str = "../knowledgebase/knowledgebase.jsonl"

    database_url: str = "postgresql+asyncpg://agent13:changeme@localhost/agent13"
    openrouter_api_key: str = ""
    openrouter_api_key_fallback: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kb13"
    web_search_model: str = "perplexity/sonar"
    env: str = "development"

    # Retention (GDPR art. 5.1.e). Termini segnaposto: da decidere con il
    # titolare prima di pubblicare un'informativa. Dry run di default.
    retention_enabled: bool = True
    retention_dry_run: bool = True
    retention_content_days: int = 730
    retention_session_days: int = 730


settings = Settings()
