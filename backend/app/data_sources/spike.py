from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_SEC_USER_AGENT = (
    "FinancialResearchAgent/0.1 local-data-source-spike "
    "(personal research; set SEC_USER_AGENT for contact)"
)


@dataclass
class ValidationResult:
    source_name: str
    category: str
    status: str
    latency_ms: int | None = None
    records_found: int = 0
    fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    snapshot_path: str | None = None


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def fetch_url(url: str, headers: dict[str, str] | None = None) -> tuple[bytes, int]:
    request_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FinancialResearchAgent/0.1)",
        "Accept": "application/json, application/rss+xml, text/csv, text/xml, */*",
    }
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        payload = response.read()
    latency_ms = int((time.perf_counter() - started) * 1000)
    return payload, latency_ms


def payload_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def safe_name(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def save_snapshot(
    raw_dir: Path,
    source_name: str,
    symbol: str,
    payload: bytes,
    suffix: str,
) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{timestamp}_{safe_name(source_name)}_{safe_name(symbol)}.{suffix}"
    path = raw_dir / filename
    path.write_bytes(payload)
    return path


def parse_stooq_csv(payload: bytes) -> tuple[list[str], int, list[str]]:
    text = payload.decode("utf-8", errors="replace")
    if text.lstrip().lower().startswith("<!doctype html") or text.lstrip().lower().startswith(
        "<html"
    ):
        return [], 0, ["Payload appears to be an HTML/browser verification page."]
    reader = csv.DictReader(text.splitlines())
    fields = list(reader.fieldnames or [])
    rows = list(reader)
    warnings: list[str] = []
    expected = {"Date", "Open", "High", "Low", "Close", "Volume"}
    missing = sorted(expected - set(fields))
    if missing:
        warnings.append(f"Missing expected price fields: {', '.join(missing)}")
    if not rows:
        warnings.append("No price rows returned.")
    return fields, len(rows), warnings


def parse_yahoo_chart(payload: bytes) -> tuple[list[str], int, list[str]]:
    data = json.loads(payload.decode("utf-8"))
    warnings: list[str] = []
    chart = data.get("chart", {})
    errors = chart.get("error")
    if errors:
        return [], 0, [f"Yahoo chart error: {errors}"]
    results = chart.get("result") or []
    if not results:
        return [], 0, ["No chart result returned."]
    first = results[0]
    timestamps = first.get("timestamp") or []
    indicators = first.get("indicators", {})
    quote = (indicators.get("quote") or [{}])[0]
    fields = ["timestamp"] + sorted(quote.keys())
    if not timestamps:
        warnings.append("No timestamps returned.")
    expected = {"open", "high", "low", "close", "volume"}
    missing = sorted(expected - set(quote.keys()))
    if missing:
        warnings.append(f"Missing expected chart fields: {', '.join(missing)}")
    return fields, len(timestamps), warnings


def parse_sec_companyfacts(payload: bytes) -> tuple[list[str], int, list[str]]:
    data = json.loads(payload.decode("utf-8"))
    warnings: list[str] = []
    facts = data.get("facts", {})
    us_gaap = facts.get("us-gaap", {})
    fields = sorted(us_gaap.keys())[:30]
    if not us_gaap:
        warnings.append("No us-gaap facts found.")
    important_metrics = {"Revenues", "NetIncomeLoss", "EarningsPerShareDiluted"}
    missing = sorted(important_metrics - set(us_gaap.keys()))
    if missing:
        warnings.append(f"Missing common metrics: {', '.join(missing)}")
    return fields, len(us_gaap), warnings


def parse_rss(payload: bytes) -> tuple[list[str], int, list[str]]:
    warnings: list[str] = []
    root = ET.fromstring(payload)
    items = root.findall(".//item")
    fields = ["title", "link", "pubDate", "description"]
    if not items:
        warnings.append("No RSS items returned.")
    return fields, len(items), warnings


def parse_json_keys(payload: bytes) -> tuple[list[str], int, list[str]]:
    data = json.loads(payload.decode("utf-8"))
    warnings: list[str] = []
    if isinstance(data, dict):
        fields = list(data.keys())
        records = len(data)
    elif isinstance(data, list):
        fields = sorted({key for row in data if isinstance(row, dict) for key in row.keys()})
        records = len(data)
    else:
        fields = []
        records = 0
        warnings.append("JSON payload is neither an object nor a list.")
    return fields, records, warnings


def status_from(warnings: list[str], errors: list[str], records_found: int) -> str:
    if errors:
        return "failed"
    if records_found <= 0:
        return "weak"
    if warnings:
        return "partial"
    return "passed"


def validate_source(
    source_name: str,
    source_config: dict[str, Any],
    instrument: dict[str, Any],
    raw_dir: Path,
) -> ValidationResult:
    category = source_config["category"]
    symbol = instrument["symbol"]
    errors: list[str] = []
    warnings: list[str] = []

    if source_config.get("api_key_env"):
        api_key_env = source_config["api_key_env"]
        api_key = os.getenv(api_key_env)
        if not api_key:
            return ValidationResult(
                source_name=source_name,
                category=category,
                status="skipped",
                warnings=[f"Skipped because {api_key_env} is not set."],
            )
    else:
        api_key = None

    if "{cik}" in source_config["url_template"] and not instrument.get("cik"):
        return ValidationResult(
            source_name=source_name,
            category=category,
            status="skipped",
            warnings=[f"Skipped because {symbol} does not have a CIK."],
        )

    url = source_config["url_template"].format(
        symbol=symbol,
        stooq_symbol=instrument.get("stooq_symbol"),
        cik=instrument.get("cik"),
        api_key=api_key,
    )
    headers = {}
    if source_name == "sec_companyfacts":
        user_agent_env = source_config.get("user_agent_env", "SEC_USER_AGENT")
        headers["User-Agent"] = os.getenv(user_agent_env, DEFAULT_SEC_USER_AGENT)

    try:
        payload, latency_ms = fetch_url(url, headers=headers)
        if source_name == "yahoo_chart_prices":
            fields, records_found, parse_warnings = parse_yahoo_chart(payload)
            suffix = "json"
        elif source_name == "stooq_prices":
            fields, records_found, parse_warnings = parse_stooq_csv(payload)
            suffix = "csv"
        elif source_name == "sec_companyfacts":
            fields, records_found, parse_warnings = parse_sec_companyfacts(payload)
            suffix = "json"
        elif source_name == "nasdaq_stock_rss":
            fields, records_found, parse_warnings = parse_rss(payload)
            suffix = "xml"
        else:
            fields, records_found, parse_warnings = parse_json_keys(payload)
            suffix = "json"
        warnings.extend(parse_warnings)
        snapshot_path = save_snapshot(raw_dir, source_name, symbol, payload, suffix)
    except urllib.error.HTTPError as exc:
        latency_ms = None
        fields = []
        records_found = 0
        snapshot_path = None
        errors.append(f"HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        latency_ms = None
        fields = []
        records_found = 0
        snapshot_path = None
        errors.append(f"URL error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001 - spike should record source-specific failures.
        latency_ms = None
        fields = []
        records_found = 0
        snapshot_path = None
        errors.append(f"{type(exc).__name__}: {exc}")

    return ValidationResult(
        source_name=source_name,
        category=category,
        status=status_from(warnings, errors, records_found),
        latency_ms=latency_ms,
        records_found=records_found,
        fields=fields,
        warnings=warnings,
        errors=errors,
        snapshot_path=str(snapshot_path) if snapshot_path else None,
    )


def init_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    schema_path = Path(__file__).resolve().parents[1] / "storage" / "source_spike_schema.sql"
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.commit()
    return connection


def start_run(connection: sqlite3.Connection, config: dict[str, Any]) -> int:
    cursor = connection.execute(
        "INSERT INTO source_validation_runs (started_at, status, config_json) VALUES (?, ?, ?)",
        (utc_now(), "running", json.dumps(config, ensure_ascii=False)),
    )
    connection.commit()
    return int(cursor.lastrowid)


def finish_run(connection: sqlite3.Connection, run_id: int, status: str) -> None:
    connection.execute(
        "UPDATE source_validation_runs SET finished_at = ?, status = ? WHERE id = ?",
        (utc_now(), status, run_id),
    )
    connection.commit()


def save_result(
    connection: sqlite3.Connection,
    run_id: int,
    result: ValidationResult,
) -> None:
    connection.execute(
        """
        INSERT INTO source_validation_results (
            run_id, source_name, category, status, latency_ms, records_found, fields_json,
            warnings_json, errors_json, snapshot_path, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            result.source_name,
            result.category,
            result.status,
            result.latency_ms,
            result.records_found,
            json.dumps(result.fields, ensure_ascii=False),
            json.dumps(result.warnings, ensure_ascii=False),
            json.dumps(result.errors, ensure_ascii=False),
            result.snapshot_path,
            utc_now(),
        ),
    )
    if result.snapshot_path:
        path = Path(result.snapshot_path)
        digest = payload_hash(path.read_bytes())
        connection.execute(
            """
            INSERT INTO raw_snapshots (
                run_id, source_name, category, payload_hash, payload_path, fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                result.source_name,
                result.category,
                digest,
                result.snapshot_path,
                utc_now(),
            ),
        )
    connection.commit()


def render_report(results: list[ValidationResult], generated_at: str) -> str:
    passed = sum(1 for result in results if result.status == "passed")
    partial = sum(1 for result in results if result.status == "partial")
    weak = sum(1 for result in results if result.status == "weak")
    failed = sum(1 for result in results if result.status == "failed")
    skipped = sum(1 for result in results if result.status == "skipped")
    lines = [
        "# 数据源验证报告",
        "",
        f"生成时间：{generated_at}",
        "",
        "## Summary",
        "",
        f"- passed: {passed}",
        f"- partial: {partial}",
        f"- weak: {weak}",
        f"- failed: {failed}",
        f"- skipped: {skipped}",
        "",
        "## Results",
        "",
        "| Source | Category | Status | Latency | Records | Fields | Warnings | Errors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        latency = f"{result.latency_ms} ms" if result.latency_ms is not None else "-"
        fields = ", ".join(result.fields[:8])
        if len(result.fields) > 8:
            fields += ", ..."
        warnings = "; ".join(result.warnings) if result.warnings else "-"
        errors = "; ".join(result.errors) if result.errors else "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    result.source_name,
                    result.category,
                    result.status,
                    latency,
                    str(result.records_found),
                    fields or "-",
                    warnings,
                    errors,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `passed` 表示该源连通、解析成功且返回了记录。",
            "- `partial` 表示可用但存在字段缺失或质量警告。",
            "- `weak` 表示连通但没有有效记录。",
            "- `failed` 表示连通或解析失败。",
            "- `skipped` 表示缺少 API key、CIK 或配置未启用。",
            "",
            "## Next Checks",
            "",
            "1. 对 passed/partial 的数据源扩大 universe 验证。",
            "2. 对 failed 的数据源确认是否是网络、限流、User-Agent 或 endpoint 变化。",
            "3. 决定 Phase 1 的首选 price、fundamentals、news 数据源组合。",
        ]
    )
    return "\n".join(lines) + "\n"


def run_validation(config_path: Path, db_path: Path, raw_dir: Path, report_path: Path) -> int:
    config = load_config(config_path)
    enabled_sources = {
        name: source for name, source in config["sources"].items() if source.get("enabled", False)
    }
    connection = init_database(db_path)
    run_id = start_run(connection, config)
    results: list[ValidationResult] = []

    try:
        for instrument in config["universe"]:
            for source_name, source_config in enabled_sources.items():
                result = validate_source(source_name, source_config, instrument, raw_dir)
                results.append(result)
                save_result(connection, run_id, result)

        overall_status = "success"
        if any(result.status == "failed" for result in results):
            overall_status = "partial"
        finish_run(connection, run_id, overall_status)
    except Exception:
        finish_run(connection, run_id, "failed")
        raise
    finally:
        connection.close()

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(results, utc_now()), encoding="utf-8")
    return 0 if not any(result.status == "failed" for result in results) else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate candidate free financial data sources.")
    parser.add_argument("--config", default="configs/data_source_spike.json", type=Path)
    parser.add_argument("--db", default="data/app.db", type=Path)
    parser.add_argument("--raw-dir", default="data/raw/source_spike", type=Path)
    parser.add_argument("--report", default="docs/data-source-validation-report.md", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_validation(args.config, args.db, args.raw_dir, args.report)


if __name__ == "__main__":
    sys.exit(main())
