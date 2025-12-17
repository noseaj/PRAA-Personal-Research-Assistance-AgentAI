import os
import requests
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

HEADERS = {
    "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get(url, params=None):
    res = requests.get(url, headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()

def post(url, payload):
    res = requests.post(url, headers=HEADERS, json=payload)
    res.raise_for_status()
    return res.json()