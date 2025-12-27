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


def extract_text_from_block(block):
    """
    paragraph / heading_1 / heading_2 / heading_3 등
    모든 rich_text 기반 block에서 텍스트 추출
    """
    block_type = block["type"]
    rich_text = block.get(block_type, {}).get("rich_text", [])

    return "".join(
        t["text"]["content"]
        for t in rich_text
    ).strip()


# ===============================
# Method section extractor
# ===============================

def extract_method_section(page_id):
    """
    Method(ALL) heading 아래의 모든 텍스트를
    다음 heading이 나올 때까지 수집
    """
    blocks = get_page_blocks(page_id)

    collecting = False
    texts = []

    for block in blocks:
        block_type = block["type"]
        text = extract_text_from_block(block)

        if not text:
            continue

        # 1️⃣ Method(ALL) 시작
        if block_type.startswith("heading") and text.strip() == "Method(ALL)":
            collecting = True
            continue

        # 2️⃣ Method 수집 중, 새로운 heading 등장 → 종료
        if collecting and block_type.startswith("heading"):
            break

        # 3️⃣ Method 내부 텍스트 수집
        if collecting:
            texts.append(text)

    return "\n".join(texts)


# ===============================
# Task loader
# ===============================

def load_tasks():
    url = f"https://api.notion.com/v1/databases/{DB_ID}/query"
    data = post(url, {})

    tasks = []

    for row in data["results"]:
        props = row["properties"]
        page_id = row["id"]

        # title
        title = (
            props["이름"]["title"][0]["text"]["content"]
            if props.get("이름", {}).get("title")
            else ""
        )

        # github url
        github = props.get("Github", {}).get("url")

        # my code path (optional)
        my_code_path = (
            props.get("MyCodePath", {})
            .get("rich_text", [{}])[0]
            .get("text", {})
            .get("content")
        )

        tasks.append({
            "title": title,
            "github": github,
            "paper_text": extract_method_section(page_id),
            "my_code_path": my_code_path,
        })

    return tasks