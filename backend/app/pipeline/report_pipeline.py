from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from backend.app.config.settings import Settings
from backend.app.reports.markdown import render_markdown_report
from backend.app.reports.pdf import render_pdf_from_markdown
from backend.app.research.local_llm import LocalLLMResearchWriter
from backend.app.screening.service import ScreeningService


@dataclass(frozen=True)
class ReportArtifacts:
    run_id: str
    markdown_path: Path
    pdf_path: Path
    candidate_count: int
    warning_count: int


class ReportPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(
        self,
        top_n: int = 10,
        horizons: tuple[str, ...] = ("short", "medium"),
        output_dir: Path | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> ReportArtifacts:
        report_progress = progress or (lambda _message: None)
        report_progress(
            "start screening; "
            f"top_n={top_n}; "
            f"config={self.settings.config_path}; "
            f"raw_dir={self.settings.raw_dir}; "
            f"report_dir={output_dir or self.settings.report_dir}"
        )
        screening = ScreeningService(self.settings).run(limit=top_n, progress=report_progress)
        if not screening.candidates:
            raise RuntimeError("No candidates were generated. Check data source connectivity.")

        report_progress(
            f"screening completed; candidates={len(screening.candidates)}, "
            f"warnings={len(screening.warnings)}"
        )
        report_progress(
            "calling local LLM; this may take up to "
            f"{self.settings.local_llm_timeout_seconds:.0f}s"
        )
        llm_report = LocalLLMResearchWriter(self.settings).write_investment_report(
            screening=screening,
            horizons=horizons,
            progress=report_progress,
        )
        report_progress("local LLM returned report content")
        report_progress("rendering Markdown and PDF")
        markdown_text = render_markdown_report(screening, llm_report, horizons)

        report_root = output_dir or self.settings.report_dir
        dated_dir = report_root / datetime.now(UTC).strftime("%Y-%m-%d")
        dated_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = dated_dir / f"investment_report_{screening.run_id}.md"
        pdf_path = dated_dir / f"investment_report_{screening.run_id}.pdf"
        markdown_path.write_text(markdown_text, encoding="utf-8")
        render_pdf_from_markdown(markdown_text, pdf_path)
        report_progress(f"artifacts written under {dated_dir}")
        return ReportArtifacts(
            run_id=screening.run_id,
            markdown_path=markdown_path,
            pdf_path=pdf_path,
            candidate_count=len(screening.candidates),
            warning_count=len(screening.warnings),
        )
