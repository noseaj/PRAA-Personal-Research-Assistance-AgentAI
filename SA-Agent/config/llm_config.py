"""
SA-Agent LLM Config
리팩토링: shared.config 사용 (하위 호환성 유지)
"""
import sys
from pathlib import Path

# shared 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import get_config

# Config 로드
_config = get_config()

# 하위 호환성을 위한 LLM_CONFIG (기존 코드가 이것을 사용함)
LLM_CONFIG = {
    "api_key": _config.openrouter_api_key,
    "base_url": _config.openrouter_url,
    "model": "anthropic/claude-sonnet-4",  # claude-sonnet-4 모델
}
