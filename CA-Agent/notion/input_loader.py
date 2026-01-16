"""
Notion 입력 모듈
수정: Database 대신 Page에서 정보를 읽는 방식 지원
"""
import os
from dotenv import load_dotenv
from notion.client import post, get

load_dotenv()

# Page ID 사용 (Database ID 대신) - fallback으로 DB_ID도 지원
INPUT_PAGE_ID = os.environ.get("NOTION_INPUT_PAGE_ID") or os.environ.get("NOTION_INPUT_DB_ID", "")


# ===============================
# Notion block helpers
# ===============================

def get_page_blocks(page_id):
    """페이지의 모든 블록 가져오기"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    try:
        res = get(url)
        return res.get("results", [])
    except Exception as e:
        print(f"[Notion] ⚠️ 블록 조회 실패: {e}")
        return []


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


def get_all_text_from_page(page_id):
    """
    페이지의 모든 텍스트 블록을 하나로 합침
    """
    blocks = get_page_blocks(page_id)
    texts = []
    
    for block in blocks:
        text = extract_text_from_block(block)
        if text:
            texts.append(text)
    
    return "\n".join(texts)


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
# Task loader (Page 기반)
# ===============================

def load_tasks():
    """
    Task 정보를 로드
    - Page 기반: INPUT_PAGE_ID의 하위 페이지들을 탐색
    - Database 기반: DB_ID에서 쿼리 (fallback)
    """
    # Page 기반 시도
    if INPUT_PAGE_ID:
        tasks = _load_tasks_from_page(INPUT_PAGE_ID)
        if tasks:
            return tasks
    
    # Database 기반 fallback
    db_id = os.environ.get("NOTION_INPUT_DB_ID")
    if db_id:
        return _load_tasks_from_database(db_id)
    
    # 둘 다 없으면 빈 리스트
    print("[Notion] ⚠️ INPUT_PAGE_ID와 INPUT_DB_ID 모두 설정되지 않았습니다")
    return []


def _load_tasks_from_page(page_id):
    """
    Page에서 Task 정보 로드
    - 하위 페이지들을 순회하며 정보 추출
    - 또는 페이지 내 블록에서 직접 정보 추출
    """
    try:
        blocks = get_page_blocks(page_id)
        tasks = []
        
        for block in blocks:
            # 하위 페이지(child_page) 타입인 경우
            if block["type"] == "child_page":
                child_id = block["id"]
                child_title = block.get("child_page", {}).get("title", "")
                
                # 하위 페이지의 내용 읽기
                child_text = get_all_text_from_page(child_id)
                
                # GitHub URL 추출 시도
                github_url = _extract_github_url(child_text)
                
                tasks.append({
                    "title": child_title,
                    "github": github_url,
                    "paper_text": child_text,
                    "my_code_path": None
                })
        
        return tasks
    except Exception as e:
        print(f"[Notion] ⚠️ Page 기반 로드 실패: {e}")
        return []


def _load_tasks_from_database(db_id):
    """
    Database에서 Task 정보 로드 (기존 방식)
    """
    try:
        url = f"https://api.notion.com/v1/databases/{db_id}/query"
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
    except Exception as e:
        print(f"[Notion] ⚠️ Database 기반 로드 실패: {e}")
        return []


def _extract_github_url(text):
    """텍스트에서 GitHub URL 추출"""
    import re
    match = re.search(r'https?://github\.com/[^\s\)]+', text)
    if match:
        return match.group(0).rstrip('.,;')
    return None
