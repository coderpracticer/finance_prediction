from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from backend.app.models.schemas import Candidate, FactorScore, ScreeningResponse


class ResearchRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_schema(self) -> None:
        schema_path = Path(__file__).resolve().parent / "mvp_schema.sql"
        with self._connection() as connection:
            connection.executescript(schema_path.read_text(encoding="utf-8"))

    def save_screening_response(self, response: ScreeningResponse) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO screening_runs (
                    id, started_at, finished_at, status, warnings_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    response.run_id,
                    now,
                    now,
                    response.status,
                    json.dumps(response.warnings, ensure_ascii=False),
                ),
            )
            connection.execute(
                """
                DELETE FROM factor_scores
                WHERE candidate_id IN (
                    SELECT id FROM candidates WHERE run_id = ?
                )
                """,
                (response.run_id,),
            )
            connection.execute("DELETE FROM candidates WHERE run_id = ?", (response.run_id,))
            for candidate in response.candidates:
                cursor = connection.execute(
                    """
                    INSERT INTO candidates (
                        run_id, symbol, name, market, rank, opportunity_score, confidence,
                        data_quality, thesis, risks_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        response.run_id,
                        candidate.symbol,
                        candidate.name,
                        candidate.market,
                        candidate.rank,
                        candidate.opportunity_score,
                        candidate.confidence,
                        candidate.data_quality,
                        candidate.thesis,
                        json.dumps(candidate.risks, ensure_ascii=False),
                    ),
                )
                candidate_id = int(cursor.lastrowid)
                for factor in candidate.factors:
                    connection.execute(
                        """
                        INSERT INTO factor_scores (
                            candidate_id, name, factor_group, score, confidence, raw_value, evidence
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            candidate_id,
                            factor.name,
                            factor.group,
                            factor.score,
                            factor.confidence,
                            None if factor.raw_value is None else str(factor.raw_value),
                            factor.evidence,
                        ),
                    )

    def get_latest_screening_response(self) -> ScreeningResponse | None:
        with self._connection() as connection:
            run = connection.execute(
                """
                SELECT * FROM screening_runs
                ORDER BY finished_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
            if run is None:
                return None
            return self.get_screening_response(str(run["id"]), connection)

    def get_screening_response(
        self,
        run_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> ScreeningResponse | None:
        owns_connection = connection is None
        if connection is None:
            connection = self._connect()
        try:
            run = connection.execute("SELECT * FROM screening_runs WHERE id = ?", (run_id,)).fetchone()
            if run is None:
                return None
            candidate_rows = connection.execute(
                """
                SELECT * FROM candidates
                WHERE run_id = ?
                ORDER BY rank ASC
                """,
                (run_id,),
            ).fetchall()
            candidates = [
                self._candidate_from_row(connection, candidate_row)
                for candidate_row in candidate_rows
            ]
            return ScreeningResponse(
                run_id=str(run["id"]),
                status=str(run["status"]),
                candidates=candidates,
                warnings=json.loads(str(run["warnings_json"])),
            )
        finally:
            if owns_connection:
                connection.close()

    def get_candidate_by_symbol(self, symbol: str) -> Candidate | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT c.*
                FROM candidates c
                JOIN screening_runs r ON r.id = c.run_id
                WHERE c.symbol = ?
                ORDER BY r.finished_at DESC, r.id DESC, c.rank ASC
                LIMIT 1
                """,
                (symbol.upper(),),
            ).fetchone()
            if row is None:
                return None
            return self._candidate_from_row(connection, row)

    def save_chat_message(self, session_id: str, role: str, content: str, symbol: str | None) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO chat_sessions (id, symbol, created_at)
                VALUES (?, ?, ?)
                """,
                (session_id, symbol, now),
            )
            connection.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, now),
            )

    def _candidate_from_row(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> Candidate:
        factor_rows = connection.execute(
            """
            SELECT * FROM factor_scores
            WHERE candidate_id = ?
            ORDER BY id ASC
            """,
            (int(row["id"]),),
        ).fetchall()
        factors = [
            FactorScore(
                name=str(factor["name"]),
                group=str(factor["factor_group"]),
                score=float(factor["score"]),
                confidence=float(factor["confidence"]),
                evidence=str(factor["evidence"]),
                raw_value=factor["raw_value"],
            )
            for factor in factor_rows
        ]
        return Candidate(
            symbol=str(row["symbol"]),
            name=str(row["name"]),
            market=str(row["market"]),
            rank=int(row["rank"]),
            opportunity_score=float(row["opportunity_score"]),
            confidence=float(row["confidence"]),
            data_quality=str(row["data_quality"]),
            factors=factors,
            thesis=str(row["thesis"]),
            risks=json.loads(str(row["risks_json"])),
        )


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def candidate_to_evidence_text(candidate: Candidate) -> str:
    factor_lines = "\n".join(
        f"- {factor.group}/{factor.name}: {factor.score:.1f}, {factor.evidence}"
        for factor in candidate.factors
    )
    return (
        f"{candidate.symbol} {candidate.name}\n"
        f"Opportunity score: {candidate.opportunity_score:.1f}\n"
        f"Confidence: {candidate.confidence:.2f}\n"
        f"Data quality: {candidate.data_quality}\n"
        f"Thesis: {candidate.thesis}\n"
        f"Risks: {', '.join(candidate.risks)}\n"
        f"Factors:\n{factor_lines}"
    )


def candidate_to_dict(candidate: Candidate) -> dict:
    return asdict(candidate)
