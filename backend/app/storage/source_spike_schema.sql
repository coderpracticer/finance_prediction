CREATE TABLE IF NOT EXISTS source_validation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms INTEGER,
    records_found INTEGER,
    fields_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    errors_json TEXT NOT NULL,
    snapshot_path TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES source_validation_runs(id)
);

CREATE TABLE IF NOT EXISTS raw_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    category TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_path TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES source_validation_runs(id)
);

