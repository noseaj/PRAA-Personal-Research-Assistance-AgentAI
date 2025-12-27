import os
from dotenv import load_dotenv
from notion.client import post
from notion.client import get
load_dotenv()

DB_ID = os.environ["NOTION_INPUT_DB_ID"]

# ===============================
# Notion block helpers
# ===============================

def get_page_blocks(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = get(url)
    return res["results"]

def extract_text_from_block(page_id):
    blocks = get_page_blocks(page_id)
    texts = []

    for block in blocks:
        block_type = block["type"]
        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
            rich_text = block.get(block_type, {}).get("rich_text", [])
            if rich_text:
                text = " ".join([t.get("plain_text", "") for t in rich_text])
                texts.append(text)

    return "\n".join(texts)

# ===============================
# Notion Content Extractor
# {
#     'title' : 제목
#     'content' : 내용
#     'url' : page_url
# }
# ===============================

def load_contents():
    url = f"https://api.notion.com/v1/databases/{DB_ID}/query"
    
    payload = {
            "sorts": [
                {
                    "timestamp": "created_time",
                    "direction": "ascending"
                }
            ]
        }
        
    all_results = []
    has_more = True
    start_cursor = None
    
    # Pagination 처리
    while has_more:
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        data = post(url, payload)
        
        all_results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    
    entries = []
    for page in all_results:
        properties = page.get("properties", {})
        title = ""
        if "Name" in properties or "이름" in properties or "Title" in properties:
            title_prop = properties.get("Name") or properties.get("이름") or properties.get("Title")
            if title_prop.get("title"):
                title = title_prop["title"][0]["plain_text"]
        
        # 페이지 내용 가져오기
        content = extract_text_from_block(page["id"])
        
        entry = {
            "title": title,
            "content": content,
            "url": page.get("url", "")
            }
        
        entries.append(entry)
    
    return entries