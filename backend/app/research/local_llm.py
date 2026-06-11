from __future__ import annotations

import json
import urllib.error
import urllib.request

from backend.app.config.settings import Settings
from backend.app.models.schemas import ScreeningResponse
from backend.app.research.prompts import build_report_prompt


class LocalLLMError(RuntimeError):
    """Raised when the configured local OpenAI-compatible LLM cannot produce a report."""


class LocalLLMResearchWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def write_investment_report(
        self,
        screening: ScreeningResponse,
        horizons: tuple[str, ...],
    ) -> str:
        prompt = build_report_prompt(screening, horizons)
        return self._call_local_llm(prompt)

    def _call_local_llm(self, prompt: str) -> str:
        url = self.settings.local_llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.local_llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是本地部署的公开市场投资研究智能体。"
                        "只能基于用户提供的结构化证据生成中文研究报告。"
                        "不要编造未提供的数据，不给确定性买卖建议。"
                        "把输出定位为研究优先级和风险提示，而不是交易指令。"
                    ),
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
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.settings.local_llm_timeout_seconds,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise LocalLLMError(
                f"Local LLM API returned HTTP {exc.code} at {url}. "
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
        return content.strip()
