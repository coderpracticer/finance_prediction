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
        warnings=["510300/eastmoney_kline_prices: timeout"],
        candidates=[
            Candidate(
                symbol="510300",
                name="沪深300ETF",
                market="CN",
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
                risks=["免费公开数据可能存在延迟。"],
            )
        ],
    )


class ReportTests(unittest.TestCase):
    def test_prompt_contains_horizons_and_candidate_evidence(self) -> None:
        prompt = build_report_prompt(sample_screening(), ("short", "medium"))

        self.assertIn("short, medium", prompt)
        self.assertIn("510300", prompt)
        self.assertIn("第一否定条件", prompt)
        self.assertIn("数据质量审计智能体", prompt)
        self.assertIn("中国 ETF 风格轮动智能体", prompt)
        self.assertIn("投资委员会评级", prompt)
        self.assertIn("仓位区间", prompt)
        self.assertIn("不构成个性化投资建议", prompt)
        self.assertIn("新手投资者", prompt)
        self.assertIn("术语解释", prompt)
        self.assertIn("ETF 是交易型开放式指数基金", prompt)
        self.assertIn("趋势失效", prompt)
        self.assertIn("事件/公告失效", prompt)

    def test_agent_prompts_define_professional_investment_team_roles(self) -> None:
        prompts = build_agent_prompts(sample_screening(), ("short", "medium"))
        names = {prompt.name for prompt in prompts}

        self.assertIn("data_quality_auditor", names)
        self.assertIn("macro_cross_asset_strategist", names)
        self.assertIn("a_share_equity_analyst", names)
        self.assertIn("china_etf_style_rotation_analyst", names)
        self.assertIn("fixed_income_fx_analyst", names)
        self.assertIn("commodity_analyst", names)
        self.assertIn("crypto_market_analyst", names)
        self.assertIn("momentum_technical_analyst", names)
        self.assertIn("news_event_analyst", names)
        self.assertIn("news_announcement_fundamental_analyst", names)
        self.assertIn("risk_challenger", names)
        self.assertIn("portfolio_sizing_advisor", names)
        self.assertIn("compliance_guardian", names)
        self.assertIn("opportunity_scout", names)

    def test_synthesis_prompt_includes_agent_outputs(self) -> None:
        prompt = build_synthesis_prompt(
            sample_screening(),
            ("short", "medium"),
            {"risk_challenger": "主要风险是价格数据缺口。"},
        )

        self.assertIn("多智能体中间结论", prompt)
        self.assertIn("risk_challenger", prompt)
        self.assertIn("主要风险是价格数据缺口。", prompt)
        self.assertIn("投资委员会主席", prompt)
        self.assertIn("合规审查", prompt)
        self.assertIn("0%-5%", prompt)
        self.assertIn("新手先看", prompt)
        self.assertIn("明确但审慎的投资建议", prompt)

    def test_markdown_report_contains_ranked_table_and_notice(self) -> None:
        markdown = render_markdown_report(
            sample_screening(),
            "## 总体结论\n这是研究优先级报告。",
            ("short", "medium"),
        )

        self.assertIn("# 中国ETF专业投资研究报告", markdown)
        self.assertIn("## 新手阅读指南", markdown)
        self.assertIn("## ETF入门说明", markdown)
        self.assertIn("ETF，中文常称“交易型开放式指数基金”", markdown)
        self.assertIn("## 投资建议口径", markdown)
        self.assertIn("完整术语表", markdown)
        self.assertIn("| 1 | 510300 | 沪深300ETF |", markdown)
        self.assertIn("## 技术附录：因子证据表", markdown)
        self.assertIn("结构化证据", markdown)
        self.assertIn("不构成个性化投资建议", markdown)

    def test_reasoning_blocks_are_removed(self) -> None:
        content = "<think>hidden reasoning</think>\n## 报告正文"

        self.assertEqual(strip_llm_reasoning(content).strip(), "## 报告正文")
        self.assertEqual(strip_markdown_reasoning(content).strip(), "## 报告正文")

    def test_cli_defaults_top_n_to_10(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["generate-report"])

        self.assertEqual(args.top_n, 10)
        self.assertEqual(args.horizons, "short,medium")

    def test_cli_supports_price_data_gate_options(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["generate-report", "--price-csv-dir", "data/prices", "--allow-weak-price-data"]
        )

        self.assertEqual(str(args.price_csv_dir), "data\\prices")
        self.assertTrue(args.allow_weak_price_data)

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
