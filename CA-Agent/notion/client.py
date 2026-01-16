import os
import requests
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

def _get_headers():
    """API 키가 포함된 헤더 반환"""
    api_key = os.environ.get('NOTION_API_KEY', '')
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

HEADERS = _get_headers()

def get(url, params=None):
    res = requests.get(url, headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()

def post(url, payload):
    res = requests.post(url, headers=HEADERS, json=payload)
    res.raise_for_status()
    return res.json()

def patch(url, payload):
    """PATCH 요청 (기존 페이지에 블록 추가용)"""
    res = requests.patch(url, headers=HEADERS, json=payload)
    res.raise_for_status()
    return res.json()
