-- Schema dell'agente 13 Protein. Idempotente: si può rilanciare su un database
-- già popolato senza effetti.

CREATE TABLE IF NOT EXISTS sessions (
    id                TEXT PRIMARY KEY,
    state             JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now(),
    completed_at      TIMESTAMPTZ,
    abandoned_at      TIMESTAMPTZ,
    is_testing        BOOLEAN NOT NULL DEFAULT false,
    total_cost        NUMERIC DEFAULT 0,
    prompt_tokens     BIGINT  DEFAULT 0,
    completion_tokens BIGINT  DEFAULT 0,
    -- colonne di reporting, riscritte a ogni save da SessionState (session.py)
    profile           TEXT,
    category          TEXT,
    format            TEXT,
    quote_requested   BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions (updated_at);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions (created_at);

CREATE TABLE IF NOT EXISTS transcripts (
    id                SERIAL PRIMARY KEY,
    session_id        TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    role              TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content           TEXT NOT NULL,
    step              TEXT,
    payload           JSONB,
    cost              NUMERIC,
    prompt_tokens     BIGINT,
    completion_tokens BIGINT,
    model             TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts (session_id);

CREATE TABLE IF NOT EXISTS evaluations (
    session_id        TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    status            TEXT NOT NULL DEFAULT 'pending',
    outcome           TEXT,
    summary           TEXT,
    friction_note     TEXT,
    quote_requested   BOOLEAN,
    model             TEXT,
    cost              NUMERIC,
    prompt_tokens     BIGINT,
    completion_tokens BIGINT,
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);

-- Un doc del knowledgebase citato in una risposta della sessione (main.py::new_topics).
CREATE TABLE IF NOT EXISTS session_topics (
    id         SERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    doc        TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_session_topics_session ON session_topics (session_id);
CREATE INDEX IF NOT EXISTS idx_session_topics_doc ON session_topics (doc);

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
