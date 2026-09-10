import importlib


def test_settings_ignores_unknown_env_file_keys(tmp_path):
    # backend/.env è condiviso con docker-compose e porta chiavi (es.
    # POSTGRES_USER) che Settings non dichiara: il caricamento non deve rompersi.
    env = tmp_path / ".env"
    env.write_text("OPENROUTER_API_KEY=test-key\nSOME_UNKNOWN_KEY=x\n")
    import config
    importlib.reload(config)
    s = config.Settings(_env_file=str(env))
    assert s.openrouter_api_key == "test-key"


def test_providers_default_to_mock_and_keyword(tmp_path):
    # Default dell'harness: l'intero stack gira senza chiavi e senza Qdrant.
    env = tmp_path / ".env"
    env.write_text("")
    import config
    s = config.Settings(_env_file=str(env))
    assert s.llm_provider == "mock"
    assert s.retrieval_provider == "keyword"
    assert s.kb_path.endswith("knowledgebase.jsonl")


def test_retention_defaults_are_dry_run(tmp_path):
    # Termini segnaposto: da fissare con il titolare prima di pubblicare
    # un'informativa. Finché sono segnaposto la purge gira in dry run.
    env = tmp_path / ".env"
    env.write_text("")
    import config
    s = config.Settings(_env_file=str(env))
    assert s.retention_enabled is True
    assert s.retention_dry_run is True
    assert s.retention_content_days == 730
    assert s.retention_session_days == 730
    assert s.retention_session_days >= s.retention_content_days
