CREATE TABLE IF NOT EXISTS screening_runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status TEXT NOT NULL,
    warnings_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    market TEXT NOT NULL,
    rank INTEGER NOT NULL,
    opportunity_score REAL NOT NULL,
    confidence REAL NOT NULL,
    data_quality TEXT NOT NULL,
    thesis TEXT NOT NULL,
    risks_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES screening_runs(id)
);

CREATE TABLE IF NOT EXISTS factor_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    factor_group TEXT NOT NULL,
    score REAL NOT NULL,
    confidence REAL NOT NULL,
    raw_value TEXT,
    evidence TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_candidates_run_rank ON candidates(run_id, rank);
CREATE INDEX IF NOT EXISTS idx_factor_scores_candidate ON factor_scores(candidate_id);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    symbol TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

