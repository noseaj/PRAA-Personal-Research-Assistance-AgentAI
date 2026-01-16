"""
PRAA 공통 설정 모듈
모든 Agent가 이 파일에서 API 키와 설정을 로드
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """
    싱글톤 패턴의 설정 클래스
    apikey.json에서 설정을 로드하고, 환경 변수로 오버라이드 가능
    """
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "Config":
        """싱글톤 인스턴스 반환"""
        return cls()
    
    def _load_config(self):
        """apikey.json 로드 및 환경 변수 처리"""
        # apikey.json 경로 찾기 (여러 위치 시도)
        possible_paths = [
            Path(__file__).parent.parent / "apikey.json",           # shared/../apikey.json
            Path.cwd() / "apikey.json",                              # 현재 디렉토리
            Path.cwd().parent / "apikey.json",                       # 상위 디렉토리
            Path(__file__).parent.parent.parent / "apikey.json",    # 더 상위
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                    break
                except Exception as e:
                    print(f"[Config] ⚠️ apikey.json 로드 실패: {e}")
        
        # 환경 변수 오버라이드
        env_mappings = {
            "OPENROUTER_API_KEY": "OpenRouterAPIKey",
            "NOTION_API_KEY": "NotionAPIKey",
            "NOTION_PAGE_ID": "NotionPageID",
            "GITHUB_TOKEN": "GitHubToken",
            "SEMANTIC_SCHOLAR_API_KEY": "SemanticScholarAPIKey",
        }
        
        for env_key, config_key in env_mappings.items():
            if os.environ.get(env_key):
                self._config[config_key] = os.environ[env_key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        return self._config.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """모든 설정 반환"""
        return self._config.copy()
    
    # ==========================================
    # 편의 프로퍼티
    # ==========================================
    
    @property
    def openrouter_api_key(self) -> Optional[str]:
        """OpenRouter API 키"""
        return self._config.get("OpenRouterAPIKey")
    
    @property
    def openrouter_url(self) -> str:
        """OpenRouter API URL"""
        return self._config.get("OpenRouterURL", "https://openrouter.ai/api/v1")
    
    @property
    def notion_api_key(self) -> Optional[str]:
        """Notion API 키"""
        return self._config.get("NotionAPIKey")
    
    @property
    def notion_page_id(self) -> Optional[str]:
        """Notion 출력 페이지 ID"""
        return self._config.get("NotionPageID")
    
    @property
    def github_token(self) -> Optional[str]:
        """GitHub Personal Access Token"""
        return self._config.get("GitHubToken")
    
    @property
    def semantic_scholar_api_key(self) -> Optional[str]:
        """Semantic Scholar API 키"""
        return self._config.get("SemanticScholarAPIKey")
    
    # ==========================================
    # Notion 환경 변수 설정 헬퍼
    # ==========================================
    
    def setup_notion_env(self):
        """Notion 관련 환경 변수 설정 (하위 Agent subprocess용)"""
        if self.notion_api_key:
            os.environ["NOTION_API_KEY"] = self.notion_api_key
        if self.notion_page_id:
            os.environ["NOTION_OUTPUT_PAGE_ID"] = self.notion_page_id
    
    def get_env_dict(self) -> Dict[str, str]:
        """subprocess에 전달할 환경 변수 딕셔너리 반환"""
        env = os.environ.copy()
        
        if self.notion_api_key:
            env["NOTION_API_KEY"] = self.notion_api_key
        if self.notion_page_id:
            env["NOTION_OUTPUT_PAGE_ID"] = self.notion_page_id
            env["NOTION_INPUT_PAGE_ID"] = self.notion_page_id
        if self.openrouter_api_key:
            env["OPENROUTER_API_KEY"] = self.openrouter_api_key
        if self.github_token:
            env["GITHUB_TOKEN"] = self.github_token
        if self.semantic_scholar_api_key:
            env["SEMANTIC_SCHOLAR_API_KEY"] = self.semantic_scholar_api_key
        
        return env


# 편의를 위한 전역 함수
def get_config() -> Config:
    """Config 싱글톤 인스턴스 반환"""
    return Config.get_instance()


def load_api_keys() -> Dict[str, Any]:
    """기존 코드 호환성을 위한 함수 (deprecated)"""
    return Config.get_instance().get_all()
