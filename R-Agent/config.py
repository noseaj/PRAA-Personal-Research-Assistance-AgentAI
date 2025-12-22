"""
R-Agent Configuration
"""
import json
from pathlib import Path

# PRAA 루트 디렉토리의 apikey.json 로드
def load_api_keys():
    praa_root = Path(__file__).parent.parent
    apikey_path = praa_root / "apikey.json"
    
    if not apikey_path.exists():
        raise FileNotFoundError(f"API key 파일을 찾을 수 없습니다: {apikey_path}")
    
    with open(apikey_path, 'r', encoding='utf-8') as f:
        return json.load(f)

API_KEYS = load_api_keys()

# Semantic Scholar API Key (선택사항)
SEMANTIC_SCHOLAR_API_KEY = API_KEYS.get("SemanticScholarAPIKey") or None

# GitHub Token (선택사항)
GITHUB_TOKEN = API_KEYS.get("GitHubToken") or None

# OpenRouter API Key
OPENROUTER_API_KEY = API_KEYS.get("OpenRouterAPIKey", "")
