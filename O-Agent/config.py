"""
O-Agent Configuration
리팩토링: shared.config 사용 (하위 호환성 유지)
"""
import sys
from pathlib import Path

# shared 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import get_config

# Config 로드
_config = get_config()

# 하위 호환성을 위한 API_KEYS (기존 코드가 이것을 사용함)
API_KEYS = _config.get_all()

# LLM 설정 (OpenRouter)
LLM_CONFIG = {
    "api_key": _config.openrouter_api_key,
    "base_url": _config.openrouter_url,
    "model": "anthropic/claude-sonnet-4",  # claude-sonnet-4 모델
    "temperature": 0.2,
}

# Notion 설정
NOTION_CONFIG = {
    "api_key": _config.notion_api_key,
    "page_id": _config.notion_page_id,
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
    "default_research_log_path": SA_AGENT_PATH / "embeddings.pkl",
}

# 출력 디렉토리 생성
O_AGENT_CONFIG["output_dir"].mkdir(exist_ok=True)
O_AGENT_CONFIG["log_dir"].mkdir(exist_ok=True)

# 하위 호환성을 위한 load_api_keys 함수
def load_api_keys():
    """deprecated: shared.config.get_config() 사용 권장"""
    return _config.get_all()
