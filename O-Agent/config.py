"""
O-Agent Configuration
API keys 및 설정 관리
"""
import json
import os
from pathlib import Path

# API keys 로드
def load_api_keys():
    """apikey.json 파일에서 API keys 로드 (PRAA 루트에서)"""
    # PRAA 루트 디렉토리의 apikey.json 사용
    praa_root = Path(__file__).parent.parent
    apikey_path = praa_root / "apikey.json"
    
    if not apikey_path.exists():
        raise FileNotFoundError(f"API key 파일을 찾을 수 없습니다: {apikey_path}")
    
    with open(apikey_path, 'r', encoding='utf-8') as f:
        keys = json.load(f)
    
    return keys

# API keys 로드
API_KEYS = load_api_keys()

# LLM 설정 (OpenRouter)
LLM_CONFIG = {
    "api_key": API_KEYS["OpenRouterAPIKey"],
    "base_url": API_KEYS["OpenRouterURL"],
    "model": "openai/gpt-3.5-turbo",  # 안정적인 유료 모델
    "temperature": 0.2,
}

# Notion 설정
NOTION_CONFIG = {
    "api_key": API_KEYS["NotionAPIKey"],
}

# Agent 경로 설정
PRAA_ROOT = Path(__file__).parent.parent
CA_AGENT_PATH = PRAA_ROOT / "CA-Agent"
R_AGENT_PATH = PRAA_ROOT / "R-Agent"
SA_AGENT_PATH = PRAA_ROOT / "SA-Agent"

# O-Agent 설정
O_AGENT_CONFIG = {
    "output_dir": Path(__file__).parent / "output",
    "log_dir": Path(__file__).parent / "logs",
    "default_research_log_path": SA_AGENT_PATH / "embeddings.pkl",  # SA-Agent 기본 경로
}

# 출력 디렉토리 생성
O_AGENT_CONFIG["output_dir"].mkdir(exist_ok=True)
O_AGENT_CONFIG["log_dir"].mkdir(exist_ok=True)
