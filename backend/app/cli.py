from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from backend.app.config.settings import get_settings
from backend.app.pipeline.report_pipeline import ReportPipeline
from backend.app.research.local_llm import LocalLLMError


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "generate-report":
        return generate_report(args)
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fra-report",
        description="Generate Markdown and PDF investment research reports from free public data.",
    )
    subparsers = parser.add_subparsers(dest="command")
    report = subparsers.add_parser("generate-report", help="run screening and generate reports")
    report.add_argument("--top-n", type=int, default=10, help="number of candidates to include")
    report.add_argument(
        "--horizons",
        default="short,medium",
        help="comma-separated horizons, default: short,medium",
    )
    report.add_argument("--config", type=Path, help="universe/data-source config path")
    report.add_argument("--database-path", type=Path, help="SQLite database path")
    report.add_argument("--raw-dir", type=Path, help="raw data snapshot directory")
    report.add_argument("--price-csv-dir", type=Path, help="directory of local OHLCV CSV files")
    report.add_argument(
        "--allow-weak-price-data",
        action="store_true",
        help="allow report generation even when price history coverage is below the gate",
    )
    report.add_argument("--output-dir", type=Path, help="report output directory")
    return parser


def generate_report(args: argparse.Namespace) -> int:
    if args.top_n < 1:
        raise SystemExit("--top-n must be >= 1")
    settings = get_settings()
    settings = replace(
        settings,
        config_path=args.config or settings.config_path,
        database_path=args.database_path or settings.database_path,
        raw_dir=args.raw_dir or settings.raw_dir,
        price_csv_dir=args.price_csv_dir or settings.price_csv_dir,
        require_price_history=False if args.allow_weak_price_data else settings.require_price_history,
        report_dir=args.output_dir or settings.report_dir,
    )
    horizons = tuple(item.strip() for item in args.horizons.split(",") if item.strip())
    if not horizons:
        raise SystemExit("--horizons must contain at least one value")
    try:
        artifacts = ReportPipeline(settings).run(
            top_n=args.top_n,
            horizons=horizons,
            output_dir=args.output_dir,
            progress=print_progress,
        )
    except LocalLLMError as exc:
        raise SystemExit(f"Local LLM configuration error: {exc}") from exc
    except RuntimeError as exc:
        raise SystemExit(f"Report generation error: {exc}") from exc

    print(f"run_id={artifacts.run_id}")
    print(f"candidates={artifacts.candidate_count}")
    print(f"warnings={artifacts.warning_count}")
    print(f"markdown={artifacts.markdown_path}")
    print(f"pdf={artifacts.pdf_path}")
    return 0


def print_progress(message: str) -> None:
    print(f"[fra-report] {message}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
