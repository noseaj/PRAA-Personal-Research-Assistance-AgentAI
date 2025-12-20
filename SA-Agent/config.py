import os
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "api_key": os.environ["OPENROUTER_API_KEY"],
    "base_url": "https://openrouter.ai/api/v1",
    "model": "google/gemini-2.0-flash-exp:free", # google/gemini-2.0-flash-exp:free | meta-llama/llama-3.1-8b-instruct:free
    "notion_token" = os.environ["NOTION_TOKEN"]
    "page_id" = os.environ["PAGE_ID"]
    "database_id" = os.environ["DATABASE_ID"]
    "embedding_model" = os.environ["EMBEDDINGMODEL"]
}