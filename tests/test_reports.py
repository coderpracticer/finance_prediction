import tempfile
import unittest
from pathlib import Path

from backend.app.cli import build_parser
from backend.app.models.schemas import Candidate, FactorScore, ScreeningResponse
from backend.app.reports.markdown import render_markdown_report
from backend.app.reports.markdown import strip_reasoning_blocks as strip_markdown_reasoning
from backend.app.reports.pdf import render_pdf_from_markdown
from backend.app.research.local_llm import strip_reasoning_blocks as strip_llm_reasoning
from backend.app.research.prompts import build_agent_prompts, build_report_prompt, build_synthesis_prompt


def sample_screening() -> ScreeningResponse:
    return ScreeningResponse(
        run_id="run-1",
        status="success",
        warnings=["AAPL/news: timeout"],
        candidates=[
            Candidate(
                symbol="AAPL",
                name="Apple Inc.",
                market="US",
                rank=1,
                opportunity_score=72.3,
                confidence=0.81,
                data_quality="good",
                factors=[
                    FactorScore(
                        name="price_momentum",
                        group="Momentum",
                        score=80.0,
                        confidence=0.9,
                        evidence="Latest close improved over lookback.",
                    )
                ],
                thesis="Momentum evidence is constructive.",
                risks=["Free public data can be delayed."],
            )
        ],
    )


class ReportTests(unittest.TestCase):
    def test_prompt_contains_horizons_and_candidate_evidence(self) -> None:
        prompt = build_report_prompt(sample_screening(), ("short", "medium"))

        self.assertIn("short, medium", prompt)
        self.assertIn("AAPL", prompt)
        self.assertIn("第一否定条件", prompt)
        self.assertIn("数据质量审计智能体", prompt)

    def test_agent_prompts_define_lightweight_roles(self) -> None:
        prompts = build_agent_prompts(sample_screening(), ("short", "medium"))
        names = {prompt.name for prompt in prompts}

        self.assertIn("data_quality_auditor", names)
        self.assertIn("momentum_technical_analyst", names)
        self.assertIn("risk_challenger", names)
        self.assertIn("opportunity_scout", names)

    def test_synthesis_prompt_includes_agent_outputs(self) -> None:
        prompt = build_synthesis_prompt(
            sample_screening(),
            ("short", "medium"),
            {"risk_challenger": "主要风险是数据缺口。"},
        )

        self.assertIn("多智能体中间结论", prompt)
        self.assertIn("risk_challenger", prompt)
        self.assertIn("主要风险是数据缺口", prompt)

    def test_markdown_report_contains_ranked_table_and_notice(self) -> None:
        markdown = render_markdown_report(
            sample_screening(),
            "## 总体结论\n这是研究优先级报告。",
            ("short", "medium"),
        )

        self.assertIn("# Investment Research Report", markdown)
        self.assertIn("| 1 | AAPL |", markdown)
        self.assertIn("not financial advice", markdown)

    def test_reasoning_blocks_are_removed(self) -> None:
        content = "<think>hidden reasoning</think>\n## 报告正文"

        self.assertEqual(strip_llm_reasoning(content).strip(), "## 报告正文")
        self.assertEqual(strip_markdown_reasoning(content).strip(), "## 报告正文")

    def test_cli_defaults_top_n_to_10(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["generate-report"])

        self.assertEqual(args.top_n, 10)
        self.assertEqual(args.horizons, "short,medium")

    def test_pdf_renderer_creates_file_when_reportlab_is_available(self) -> None:
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("reportlab is not installed in the current local environment")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.pdf"
            render_pdf_from_markdown("# 测试报告\n\n中文 PDF 内容", output_path)

            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
