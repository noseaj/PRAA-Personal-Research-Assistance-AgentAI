import os
from config import *
from dotenv import load_dotenv
import requests
import json
from typing import Dict, List, Optional
from config import LLM_CONFIG

load_dotenv()

NOTION_TOKEN = LLM_CONFIG["notion_token"]
PAGE_ID = LLM_CONFIG["pagd_id"]
DATABASE_ID = LLM_CONFIG["database_id"]


class Notion:
    def __init__(self, notion_token: str):
        """
        Notion API 클라이언트 초기화
        
        Args:
            notion_token: Notion Integration Token
        """
        self.token = notion_token
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"
    
    def get_database(self, database_id: str) -> Dict:
        """ 데이터베이스 정보 가져오기 """
        url = f"{self.base_url}/databases/{database_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def query_database(self, database_id: str, filter_params: Optional[Dict] = None) -> List[Dict]:
        """ 데이터베이스 쿼리 """
        url = f"{self.base_url}/databases/{database_id}/query"
        payload = {}
        if filter_params:
            payload = filter_params
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()["results"]
    
    def get_page(self, page_id: str) -> Dict:
        """ 페이지 정보 가져오기 """
        url = f"{self.base_url}/pages/{page_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_page_content(self, page_id: str) -> List[Dict]:
        """ 페이지 블록 가져오기 """
        url = f"{self.base_url}/blocks/{page_id}/children"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()["results"]
    
    def extract_text_from_rich_text(self, rich_text: List[Dict]) -> str:
        """ Rich text 형식에서 텍스트 추출 """
        return "".join([text["plain_text"] for text in rich_text])
    
    def extract_properties(self, page: Dict) -> Dict[str, str]:
        """ 페이지 속성 추출 """
        properties = {}
        for prop_name, prop_value in page["properties"].items():
            prop_type = prop_value["type"]
            
            if prop_type == "title":
                properties[prop_name] = self.extract_text_from_rich_text(prop_value["title"])
            elif prop_type == "rich_text":
                properties[prop_name] = self.extract_text_from_rich_text(prop_value["rich_text"])
            elif prop_type == "select" and prop_value["select"]:
                properties[prop_name] = prop_value["select"]["name"]
            elif prop_type == "multi_select":
                properties[prop_name] = ", ".join([item["name"] for item in prop_value["multi_select"]])
            elif prop_type == "date" and prop_value["date"]:
                properties[prop_name] = prop_value["date"]["start"]
            elif prop_type == "number" and prop_value["number"]:
                properties[prop_name] = str(prop_value["number"])
            elif prop_type == "checkbox":
                properties[prop_name] = str(prop_value["checkbox"])
            elif prop_type == "url" and prop_value["url"]:
                properties[prop_name] = prop_value["url"]
            elif prop_type == "email" and prop_value["email"]:
                properties[prop_name] = prop_value["email"]
            elif prop_type == "phone_number" and prop_value["phone_number"]:
                properties[prop_name] = prop_value["phone_number"]
        
        return properties
    
    def extract_block_text(self, block: Dict) -> str:
        """ 블록에서 텍스트 추출 """
        block_type = block["type"]
        text_content = ""
        
        if block_type == "paragraph":
            text_content = self.extract_text_from_rich_text(block["paragraph"]["rich_text"])
        elif block_type == "heading_1":
            text_content = "# " + self.extract_text_from_rich_text(block["heading_1"]["rich_text"])
        elif block_type == "heading_2":
            text_content = "## " + self.extract_text_from_rich_text(block["heading_2"]["rich_text"])
        elif block_type == "heading_3":
            text_content = "### " + self.extract_text_from_rich_text(block["heading_3"]["rich_text"])
        elif block_type == "bulleted_list_item":
            text_content = "- " + self.extract_text_from_rich_text(block["bulleted_list_item"]["rich_text"])
        elif block_type == "numbered_list_item":
            text_content = "1. " + self.extract_text_from_rich_text(block["numbered_list_item"]["rich_text"])
        elif block_type == "to_do":
            checked = "✓" if block["to_do"]["checked"] else "☐"
            text_content = f"{checked} " + self.extract_text_from_rich_text(block["to_do"]["rich_text"])
        elif block_type == "code":
            code_text = self.extract_text_from_rich_text(block["code"]["rich_text"])
            text_content = f"```{block['code']['language']}\n{code_text}\n```"
        elif block_type == "quote":
            text_content = "> " + self.extract_text_from_rich_text(block["quote"]["rich_text"])
        
        return text_content
    
    def page_to_input(self, page_id: str, include_properties: bool = True) -> str:
        # 페이지 정보 가져오기
        page = self.get_page(page_id)
        llm_input = []
        
        # 페이지 속성 추가
        # if include_properties:
        #     properties = self.extract_properties(page)
        #     if properties:
        #         for key, value in properties.items():
        #             # llm_input.append(f"{key}: {value}")
        #         llm_input.append("")
        
        # 페이지 콘텐츠 추가
        blocks = self.get_page_content(page_id)
        for block in blocks:
            text = self.extract_block_text(block)
            if text:
                llm_input.append(text)
        
        return "\n".join(llm_input)
    
    def database_to_input(self, database_id: str, max_pages: Optional[int] = None) -> str:
        # 데이터베이스 쿼리
        pages = self.query_database(database_id)
        
        if max_pages:
            pages = pages[:max_pages]
        
        llm_input = []
        
        for i, page in enumerate(pages, 1):
            properties = self.extract_properties(page)
            llm_input.append(f"\n{'='*50}")
            llm_input.append(f"항목 {i}")
            llm_input.append('='*50)
            
            for key, value in properties.items():
                llm_input.append(f"{key}: {value}")
        
        return "\n".join(llm_input)


