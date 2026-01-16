"""
PRAA Notion API 클라이언트 (공통)
모든 Agent가 공유하는 Notion HTTP 클라이언트
"""
import os
import requests
from typing import Dict, Any, Optional
from shared.config import get_config


class NotionClient:
    """
    Notion API HTTP 클라이언트
    """
    
    BASE_URL = "https://api.notion.com/v1"
    API_VERSION = "2022-06-28"
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Notion API 키 (없으면 Config에서 로드)
        """
        config = get_config()
        self.api_key = api_key or config.notion_api_key or os.environ.get("NOTION_API_KEY")
        
        if not self.api_key:
            raise ValueError("Notion API 키가 설정되지 않았습니다")
    
    def _headers(self) -> Dict[str, str]:
        """API 요청 헤더"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": self.API_VERSION,
            "Content-Type": "application/json"
        }
    
    def get(self, endpoint: str) -> Dict[str, Any]:
        """
        GET 요청
        
        Args:
            endpoint: API 엔드포인트 (전체 URL 또는 상대 경로)
        """
        url = endpoint if endpoint.startswith("http") else f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST 요청
        
        Args:
            endpoint: API 엔드포인트
            data: 요청 데이터
        """
        url = endpoint if endpoint.startswith("http") else f"{self.BASE_URL}{endpoint}"
        response = requests.post(url, headers=self._headers(), json=data)
        response.raise_for_status()
        return response.json()
    
    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        PATCH 요청
        
        Args:
            endpoint: API 엔드포인트
            data: 요청 데이터
        """
        url = endpoint if endpoint.startswith("http") else f"{self.BASE_URL}{endpoint}"
        response = requests.patch(url, headers=self._headers(), json=data)
        response.raise_for_status()
        return response.json()
    
    # ==========================================
    # 편의 메서드
    # ==========================================
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """페이지 정보 조회"""
        return self.get(f"/pages/{page_id}")
    
    def get_block_children(self, block_id: str) -> Dict[str, Any]:
        """블록 하위 항목 조회"""
        return self.get(f"/blocks/{block_id}/children")
    
    def append_block_children(self, block_id: str, children: list) -> Dict[str, Any]:
        """블록 하위에 콘텐츠 추가"""
        return self.patch(f"/blocks/{block_id}/children", {"children": children})
    
    def create_page(
        self,
        parent_id: str,
        title: str,
        children: list = None,
        is_database: bool = False
    ) -> Dict[str, Any]:
        """
        새 페이지 생성
        
        Args:
            parent_id: 부모 페이지/데이터베이스 ID
            title: 페이지 제목
            children: 초기 블록 콘텐츠
            is_database: 부모가 데이터베이스인지 여부
        """
        if is_database:
            parent = {"database_id": parent_id}
        else:
            parent = {"page_id": parent_id}
        
        payload = {
            "parent": parent,
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            }
        }
        
        if children:
            payload["children"] = children
        
        return self.post("/pages", payload)


# ==========================================
# 싱글톤 인스턴스 및 편의 함수
# ==========================================

_client: Optional[NotionClient] = None


def get_notion_client() -> NotionClient:
    """Notion 클라이언트 싱글톤 인스턴스 반환"""
    global _client
    if _client is None:
        _client = NotionClient()
    return _client


def get(url: str) -> Dict[str, Any]:
    """GET 요청 (편의 함수)"""
    return get_notion_client().get(url)


def post(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """POST 요청 (편의 함수)"""
    return get_notion_client().post(url, data)


def patch(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """PATCH 요청 (편의 함수)"""
    return get_notion_client().patch(url, data)
