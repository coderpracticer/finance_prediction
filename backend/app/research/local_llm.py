from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable

from backend.app.config.settings import Settings
from backend.app.models.schemas import ScreeningResponse
from backend.app.research.prompts import build_agent_prompts, build_synthesis_prompt


class LocalLLMError(RuntimeError):
    """Raised when the configured local OpenAI-compatible LLM cannot produce a report."""


class LocalLLMResearchWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def write_investment_report(
        self,
        screening: ScreeningResponse,
        horizons: tuple[str, ...],
        progress: Callable[[str], None] | None = None,
    ) -> str:
        agent_outputs: dict[str, str] = {}
        for agent_prompt in build_agent_prompts(screening, horizons):
            if progress:
                progress(f"calling agent: {agent_prompt.name}")
            agent_outputs[agent_prompt.name] = self._call_local_llm(
                agent_prompt.user_prompt,
                system_prompt=agent_prompt.system_prompt,
                progress=progress,
                agent_name=agent_prompt.name,
            )
        synthesis_prompt = build_synthesis_prompt(screening, horizons, agent_outputs)
        if progress:
            progress("calling agent: final_research_writer")
        return self._call_local_llm(
            synthesis_prompt,
            system_prompt=(
                "你是专业投资团队的最终研究写作智能体。你负责综合多个专业智能体的中间结论，"
                "生成面向普通投资者的中文投资研究报告。只能基于提供的结构化证据和中间结论，"
                "不得编造未提供的数据，不得承诺收益，不得给出确定性买卖指令。"
                "可以给出审慎评级、建议动作、仓位区间、第一失效条件和后续观察清单。"
                "必须明确说明报告不构成个性化投资建议、收益承诺或交易指令。"
                "不要输出 <think> 或内部推理草稿。"
            ),
            progress=progress,
            agent_name="final_research_writer",
        )

    def _call_local_llm(
        self,
        prompt: str,
        system_prompt: str,
        progress: Callable[[str], None] | None = None,
        agent_name: str = "local_llm",
    ) -> str:
        url = self.settings.local_llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.local_llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
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
        if progress:
            progress(f"POST {url}; agent={agent_name}; model={self.settings.local_llm_model}")
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.settings.local_llm_timeout_seconds,
            ) as response:
                if progress:
                    progress(f"local LLM HTTP {response.status}; reading response")
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise LocalLLMError(
                f"Local LLM API returned HTTP {exc.code} at {url}. "
                f"Requested model={self.settings.local_llm_model!r}. "
                f"Check LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL, and API key. {body[:300]}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LocalLLMError(
                f"Cannot reach local LLM API at {url}. "
                "Check that the OpenAI-compatible server is running on the 2x4090 host."
            ) from exc
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            raise LocalLLMError("Local LLM API returned an invalid chat/completions response.") from exc

        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise LocalLLMError("Local LLM API returned an empty report.")
        return strip_reasoning_blocks(content).strip()


def strip_reasoning_blocks(content: str) -> str:
    while True:
        start = content.find("<think>")
        end = content.find("</think>")
        if start == -1 or end == -1 or end < start:
            return content
        content = content[:start] + content[end + len("</think>") :]
