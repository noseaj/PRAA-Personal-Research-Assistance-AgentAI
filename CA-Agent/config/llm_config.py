import os
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "api_key": os.environ["OPENROUTER_API_KEY"],
    "base_url": "https://openrouter.ai/api/v1",
    "model": "meta-llama/llama-3.1-8b-instruct",
}
