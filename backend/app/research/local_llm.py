from __future__ import annotations

import json
import urllib.error
import urllib.request

from backend.app.config.settings import Settings
from backend.app.models.schemas import Candidate, FactorScore, InstrumentDataset


class LocalLLMResearchWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def write_candidate_note(
        self,
        dataset: InstrumentDataset,
        factors: list[FactorScore],
        score: float,
        confidence: float,
        data_quality: str,
    ) -> tuple[str, list[str]]:
        prompt = build_research_prompt(dataset, factors, score, confidence, data_quality)
        try:
            thesis = self._call_local_llm(prompt)
            if thesis:
                return thesis, default_risks(data_quality)
        except Exception:
            pass
        return fallback_note(dataset, factors, score, confidence, data_quality), default_risks(data_quality)

    def answer_question(self, evidence: str, question: str) -> str:
        prompt = (
            "以下是候选标的的结构化研究证据。请只基于这些证据回答用户问题，"
            "用中文，回答要具体、克制，并指出不确定性。\n\n"
            f"证据：\n{evidence}\n\n"
            f"用户问题：{question}"
        )
        try:
            answer = self._call_local_llm(prompt)
            if answer:
                return answer
        except Exception:
            pass
        return (
            "当前本地 LLM API 不可用，先给出规则降级回答：这个候选的判断只能基于已保存的"
            "因子、机会分、风险和数据质量。建议优先检查最高贡献因子是否仍然成立，同时关注"
            "风险项和数据质量；在没有更多证据前，不应把它视为确定性买卖结论。"
        )

    def _call_local_llm(self, prompt: str) -> str | None:
        url = self.settings.local_llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.local_llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是本地部署的投资研究助理。只基于给定证据生成中文研究解释，"
                        "必须标注不确定性，不给确定性买卖建议。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.local_llm_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.settings.local_llm_timeout_seconds,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError):
            return None
        return data.get("choices", [{}])[0].get("message", {}).get("content")


def build_research_prompt(
    dataset: InstrumentDataset,
    factors: list[FactorScore],
    score: float,
    confidence: float,
    data_quality: str,
) -> str:
    factor_lines = "\n".join(
        f"- {factor.group}/{factor.name}: score={factor.score:.1f}, "
        f"confidence={factor.confidence:.2f}, evidence={factor.evidence}"
        for factor in factors
    )
    news_titles = "\n".join(f"- {item.title}" for item in dataset.news[:5]) or "- No news items"
    return (
        f"标的：{dataset.instrument.symbol} {dataset.instrument.name}\n"
        f"综合机会分：{score:.2f}\n"
        f"置信度：{confidence:.2f}\n"
        f"数据质量：{data_quality}\n\n"
        f"因子证据：\n{factor_lines}\n\n"
        f"近期新闻标题：\n{news_titles}\n\n"
        "请输出一段 120-180 字中文研究解释，偏机会挖掘型，但必须包含主要风险。"
    )


def fallback_note(
    dataset: InstrumentDataset,
    factors: list[FactorScore],
    score: float,
    confidence: float,
    data_quality: str,
) -> str:
    top_factors = sorted(factors, key=lambda factor: factor.score, reverse=True)[:2]
    positives = "；".join(f"{factor.group} 信号 {factor.score:.1f}" for factor in top_factors)
    return (
        f"{dataset.instrument.symbol} 值得进入观察名单，当前综合机会分为 {score:.1f}，"
        f"主要支撑来自 {positives or '有限的可用数据'}。这更像是机会线索而非高置信度结论，"
        f"因为当前置信度为 {confidence:.2f}，数据质量为 {data_quality}。后续应继续核验基本面、"
        "新闻催化是否持续，以及价格信号是否出现反转。"
    )


def default_risks(data_quality: str) -> list[str]:
    risks = ["免费数据源可能存在延迟、字段缺失或接口变化。", "机会分只用于研究筛选，不构成买卖建议。"]
    if data_quality != "good":
        risks.append("当前数据质量不足以支持高置信度结论。")
    return risks
