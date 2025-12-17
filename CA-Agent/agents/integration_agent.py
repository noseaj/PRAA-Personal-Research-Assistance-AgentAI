from openai import OpenAI
import json
from config.llm_config import LLM_CONFIG
from utils.prompt_loader import load_prompt


class IntegrationAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
        self.prompt = load_prompt("integration_prompt.txt")

    def run(self, reference_analysis, my_code_analysis):
        prompt = self.prompt.format(
            reference_analysis=reference_analysis,
            my_code_analysis=my_code_analysis,
        )

        res = self.client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        raw = res.choices[0].message.content
        if not raw:
            return self._fallback("Empty LLM response")

        raw = raw.strip()

        # 1️⃣ ```json 코드블록 제거
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        # 2️⃣ JSON 파싱 시도
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return self._fallback(raw)

    def _fallback(self, raw_text):
        """
        LLM이 JSON을 안 지켰을 때도
        파이프라인이 안 죽도록 보장
        """
        return {
            "analysis_en": {
                "matches": [],
                "recommendations": []
            },
            "summary_ko": {
                "matches": [],
                "recommendations": [
                    {
                        "function": "UNKNOWN",
                        "description": raw_text
                    }
                ]
            }
        }
