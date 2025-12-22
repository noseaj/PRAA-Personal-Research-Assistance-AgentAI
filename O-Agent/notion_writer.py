"""
O-Agent 전용 Notion Writer
CA-Agent 코드를 수정하지 않고 O-Agent에서 사용
"""
import requests

class NotionWriter:
    def __init__(self, api_key, database_id):
        self.api_key = api_key
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
    
    def write_page(self, title, content):
        """
        Notion 데이터베이스에 페이지 작성
        
        Args:
            title: 페이지 제목 (Title 속성)
            content: 페이지 내용 (본문)
        
        Returns:
            response: Notion API 응답
        """
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "이름": {  # 실제 데이터베이스의 Title 속성 이름
                    "title": [
                        {"text": {"content": title[:200]}}  # Notion title 길이 제한
                    ]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"text": {"content": content[:2000]}}  # 너무 긴 내용 제한
                        ]
                    }
                }
            ]
        }
        
        url = "https://api.notion.com/v1/pages"
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
