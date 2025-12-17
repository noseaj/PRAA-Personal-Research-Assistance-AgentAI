from openai import OpenAI
import json
from config.llm_config import LLM_CONFIG
from utils.prompt_loader import load_prompt


class ReferenceAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
        self.prompt = load_prompt("reference_prompt.txt")

    def run(self, paper_text, functions):
        # ✅ 함수 정보를 조금 더 풍부하게 전달
        func_text = "\n".join(
            f"- File: {f['file']}\n  Function: {f['name']}"
            for f in functions
        )

        prompt = self.prompt.format(
            paper_text=paper_text,
            functions=func_text,
        )

        res = self.client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        raw = res.choices[0].message.content
        if not raw:
            return {"paper_concepts": []}

        raw = raw.strip()

        # ✅ 코드블록 제거
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        # ✅ JSON 파싱 방어
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "paper_concepts": [],
                "raw_output": raw
            }
