from openai import OpenAI
from config.llm_config import LLM_CONFIG
from utils.prompt_loader import load_prompt


class AnswerAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
        self.prompt = load_prompt("answer_prompt.txt")

    def answer(
        self,
        user_query: str,
        reference_analysis: str,
        my_code_analysis: str,
        integration_result,
    ):
        prompt = self.prompt.format(
            user_query=user_query,
            reference_analysis=reference_analysis,
            my_code_analysis=my_code_analysis,
            integration_result=integration_result,
        )

        res = self.client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return res.choices[0].message.content.strip()
