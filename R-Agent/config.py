"""
R-Agent Config
리팩토링: shared.config 사용 (하위 호환성 유지)
"""
import sys
from pathlib import Path

# shared 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import get_config

# Config 로드
_config = get_config()

# 하위 호환성을 위한 변수들 (기존 코드가 이것을 사용함)
SEMANTIC_SCHOLAR_API_KEY = _config.semantic_scholar_api_key or _config.get("SemanticScholarAPIKey", "")
GITHUB_TOKEN = _config.github_token or _config.get("GitHubToken", "")
