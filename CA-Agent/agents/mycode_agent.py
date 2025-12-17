from openai import OpenAI
from config.llm_config import LLM_CONFIG
from utils.prompt_loader import load_prompt

class MyCodeAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
        self.prompt = load_prompt("mycode_prompt.txt")

    def run(self, functions):
        func_text = "\n".join(
            f"- {f['file']}::{f['name']}" for f in functions
        )

        prompt = self.prompt.format(functions=func_text)

        res = self.client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return res.choices[0].message.content
