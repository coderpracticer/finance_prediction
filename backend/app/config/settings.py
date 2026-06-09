from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Financial Research Agent"
    config_path: Path = Path("configs/data_source_spike.json")
    database_path: Path = Path("data/app.db")
    raw_dir: Path = Path("data/raw/mvp")
    local_llm_base_url: str = "http://localhost:8000/v1"
    local_llm_api_key: str = "local"
    local_llm_model: str = "local-finance-agent"
    local_llm_timeout_seconds: float = 60.0


def get_settings() -> Settings:
    return Settings(
        config_path=Path(os.getenv("FRA_CONFIG_PATH", "configs/data_source_spike.json")),
        database_path=Path(os.getenv("FRA_DATABASE_PATH", "data/app.db")),
        raw_dir=Path(os.getenv("FRA_RAW_DIR", "data/raw/mvp")),
        local_llm_base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8000/v1"),
        local_llm_api_key=os.getenv("LOCAL_LLM_API_KEY", "local"),
        local_llm_model=os.getenv("LOCAL_LLM_MODEL", "local-finance-agent"),
        local_llm_timeout_seconds=float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "60")),
    )

