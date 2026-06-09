from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, Query

from backend.app.config.settings import get_settings
from backend.app.research.local_llm import LocalLLMResearchWriter
from backend.app.screening.service import ScreeningService
from backend.app.storage.repository import ResearchRepository, candidate_to_dict, candidate_to_evidence_text


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings")
def settings_summary() -> dict[str, str]:
    settings = get_settings()
    return {
        "config_path": str(settings.config_path),
        "database_path": str(settings.database_path),
        "raw_dir": str(settings.raw_dir),
        "local_llm_base_url": settings.local_llm_base_url,
        "local_llm_model": settings.local_llm_model,
    }


@router.post("/screening-runs")
def run_screening(limit: int = Query(default=10, ge=1, le=50)) -> dict:
    service = ScreeningService(get_settings())
    return service.run(limit=limit).to_dict()


@router.get("/screening-runs/latest")
def latest_screening_run() -> dict:
    service = ScreeningService(get_settings())
    response = service.latest()
    if response is None:
        return {"run_id": None, "status": "empty", "candidates": [], "warnings": []}
    return response.to_dict()


@router.get("/candidates/{symbol}")
def candidate_detail(symbol: str) -> dict:
    repository = ResearchRepository(get_settings().database_path)
    candidate = repository.get_candidate_by_symbol(symbol)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"No candidate found for {symbol.upper()}.")
    return candidate_to_dict(candidate)


@router.post("/chat/messages")
def chat_message(payload: dict = Body(...)) -> dict:
    settings = get_settings()
    symbol = str(payload.get("symbol") or "").upper() or None
    message = str(payload.get("message") or "").strip()
    session_id = str(payload.get("session_id") or uuid4())
    if not message:
        raise HTTPException(status_code=400, detail="message is required.")

    repository = ResearchRepository(settings.database_path)
    candidate = repository.get_candidate_by_symbol(symbol) if symbol else None
    if symbol and candidate is None:
        raise HTTPException(status_code=404, detail=f"No candidate found for {symbol}.")

    evidence = candidate_to_evidence_text(candidate) if candidate else "No candidate context."
    writer = LocalLLMResearchWriter(settings)
    answer = writer.answer_question(evidence=evidence, question=message)

    repository.save_chat_message(session_id, "user", message, symbol)
    repository.save_chat_message(session_id, "assistant", answer, symbol)
    return {
        "session_id": session_id,
        "symbol": symbol,
        "answer": answer,
        "used_candidate_context": candidate is not None,
    }
