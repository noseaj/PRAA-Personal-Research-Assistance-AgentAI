"""
Notion 출력 모듈
수정: Base Page 하위에 Task ID 기반 새 페이지 생성
"""
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from notion.client import patch, post, get

load_dotenv()

# Base Page ID - 이 페이지 하위에 새 페이지가 생성됨
BASE_PAGE_ID = os.environ.get("NOTION_OUTPUT_PAGE_ID") or os.environ.get("NOTION_OUTPUT_DB_ID", "")


def generate_task_id() -> str:
    """고유한 Task ID 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"TASK_{timestamp}_{short_uuid}"


def _sanitize_text(text: str) -> str:
    """
    Notion API에서 문제가 될 수 있는 특수 문자 처리
    """
    if not text:
        return ""
    # 특수 제어 문자 제거
    import re
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


def _split_text_to_blocks(text: str, max_length: int = 1500):
    """
    긴 텍스트를 여러 블록으로 분할
    Notion API는 블록당 2000자 제한이 있음 (안전하게 1500자)
    """
    text = _sanitize_text(text)
    
    if not text:
        return []
    
    blocks = []
    lines = text.split('\n')
    current_block = ""
    
    for line in lines:
        # 라인 자체가 max_length를 초과하면 분할
        if len(line) > max_length:
            if current_block:
                blocks.append(current_block.strip())
                current_block = ""
            # 긴 라인 분할
            for i in range(0, len(line), max_length):
                blocks.append(line[i:i+max_length])
        elif len(current_block) + len(line) + 1 <= max_length:
            current_block += line + '\n'
        else:
            if current_block:
                blocks.append(current_block.strip())
            current_block = line + '\n'
    
    if current_block.strip():
        blocks.append(current_block.strip())
    
    return blocks


def create_task_page(
    task_id: str,
    title: str,
    agent_type: str = "CA-Agent"
) -> dict:
    """
    Base Page 하위에 새로운 Task 페이지 생성
    
    Args:
        task_id: 고유한 Task ID
        title: 페이지 제목
        agent_type: Agent 유형 (CA-Agent, R-Agent, SA-Agent)
        
    Returns:
        생성된 페이지 정보 (id 포함)
    """
    if not BASE_PAGE_ID:
        print("[Notion] ⚠️ BASE_PAGE_ID가 설정되지 않았습니다")
        return None
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    page_title = f"[{agent_type}] {title} ({task_id})"
    
    # 새 페이지 생성 payload
    payload = {
        "parent": {"page_id": BASE_PAGE_ID},
        "properties": {
            "title": {
                "title": [{"text": {"content": page_title}}]
            }
        },
        "children": [
            # 메타 정보
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "🔖"},
                    "rich_text": [{
                        "text": {
                            "content": f"Task ID: {task_id}\nAgent: {agent_type}\n생성 시간: {timestamp}"
                        }
                    }]
                }
            },
            # 구분선
            {"object": "block", "type": "divider", "divider": {}}
        ]
    }
    
    try:
        result = post("https://api.notion.com/v1/pages", payload)
        print(f"[Notion] ✅ 새 페이지 생성: {page_title}")
        return result
    except Exception as e:
        print(f"[Notion] ❌ 페이지 생성 실패: {e}")
        return None


def append_to_page(page_id: str, blocks: list) -> dict:
    """
    기존 페이지에 블록 추가
    Notion API는 한 번에 최대 100개 블록 추가 가능
    
    Args:
        page_id: 페이지 ID
        blocks: 추가할 블록 리스트
        
    Returns:
        응답 결과
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    # 100개씩 나눠서 추가
    MAX_BLOCKS = 100
    results = []
    
    for i in range(0, len(blocks), MAX_BLOCKS):
        batch = blocks[i:i+MAX_BLOCKS]
        payload = {"children": batch}
        
        try:
            result = patch(url, payload)
            results.append(result)
        except Exception as e:
            print(f"[Notion] ❌ 블록 추가 실패: {e}")
            return None
    
    return results[-1] if results else None


def write_qna_answer(
    question: str,
    answer: str,
    task_id: str = None,
    agent_type: str = "CA-Agent"
) -> dict:
    """
    Q&A 결과를 새로운 Task 페이지에 작성
    
    Args:
        question: 사용자 질문
        answer: AI 응답
        task_id: Task ID (없으면 자동 생성)
        agent_type: Agent 유형
        
    Returns:
        생성된 페이지 정보 및 task_id
    """
    if task_id is None:
        task_id = generate_task_id()
    
    # 새 페이지 생성
    page = create_task_page(
        task_id=task_id,
        title=question[:50] + "..." if len(question) > 50 else question,
        agent_type=agent_type
    )
    
    if not page:
        return {"status": "failed", "task_id": task_id}
    
    page_id = page.get("id")
    
    # 질문 블록
    question_blocks = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"text": {"content": "❓ 질문"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": question}}]
            }
        },
        {"object": "block", "type": "divider", "divider": {}}
    ]
    
    # 답변 블록
    answer_blocks = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"text": {"content": "💡 답변"}}]
            }
        }
    ]
    
    # 긴 답변 분할
    for block_text in _split_text_to_blocks(answer):
        answer_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": block_text}}]
            }
        })
    
    # 블록 추가
    append_to_page(page_id, question_blocks + answer_blocks)
    
    print(f"[Notion] ✅ Q&A 결과 작성 완료 (Task ID: {task_id})")
    
    return {
        "status": "success",
        "task_id": task_id,
        "page_id": page_id,
        "page_url": page.get("url")
    }


def write_analysis_result(
    title: str,
    content: str,
    metadata: dict = None,
    task_id: str = None,
    agent_type: str = "CA-Agent"
) -> dict:
    """
    분석 결과를 새로운 Task 페이지에 작성
    
    Args:
        title: 결과 제목
        content: 분석 내용
        metadata: 추가 메타데이터 (paper_name, github_url 등)
        task_id: Task ID (없으면 자동 생성)
        agent_type: Agent 유형
        
    Returns:
        생성된 페이지 정보 및 task_id
    """
    if task_id is None:
        task_id = generate_task_id()
    
    # 새 페이지 생성
    page = create_task_page(
        task_id=task_id,
        title=title,
        agent_type=agent_type
    )
    
    if not page:
        return {"status": "failed", "task_id": task_id}
    
    page_id = page.get("id")
    
    blocks = []
    
    # 메타데이터가 있으면 추가
    if metadata:
        meta_text = []
        if metadata.get("paper_name"):
            meta_text.append(f"📄 논문: {metadata['paper_name']}")
        if metadata.get("github_url"):
            meta_text.append(f"🔗 GitHub: {metadata['github_url']}")
        if metadata.get("local_code_path"):
            meta_text.append(f"📁 로컬 코드: {metadata['local_code_path']}")
        
        if meta_text:
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "ℹ️"},
                    "rich_text": [{"text": {"content": "\n".join(meta_text)}}]
                }
            })
            blocks.append({"object": "block", "type": "divider", "divider": {}})
    
    # 내용 추가
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"text": {"content": "📊 분석 결과"}}]
        }
    })
    
    for block_text in _split_text_to_blocks(content):
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": block_text}}]
            }
        })
    
    # 블록 추가
    append_to_page(page_id, blocks)
    
    print(f"[Notion] ✅ 분석 결과 작성 완료 (Task ID: {task_id})")
    
    return {
        "status": "success",
        "task_id": task_id,
        "page_id": page_id,
        "page_url": page.get("url")
    }


def get_task_pages(task_id: str = None) -> list:
    """
    Base Page 하위의 Task 페이지들 조회
    
    Args:
        task_id: 특정 Task ID (없으면 모든 Task)
        
    Returns:
        Task 페이지 리스트
    """
    if not BASE_PAGE_ID:
        return []
    
    try:
        url = f"https://api.notion.com/v1/blocks/{BASE_PAGE_ID}/children"
        result = get(url)
        
        pages = []
        for block in result.get("results", []):
            if block["type"] == "child_page":
                page_title = block.get("child_page", {}).get("title", "")
                page_id = block["id"]
                
                # task_id 필터링
                if task_id:
                    if task_id in page_title:
                        pages.append({
                            "id": page_id,
                            "title": page_title
                        })
                else:
                    pages.append({
                        "id": page_id,
                        "title": page_title
                    })
        
        return pages
    except Exception as e:
        print(f"[Notion] ❌ Task 페이지 조회 실패: {e}")
        return []


def aggregate_task_results(task_id: str) -> dict:
    """
    특정 Task ID에 해당하는 모든 결과를 집계
    
    Args:
        task_id: 집계할 Task ID
        
    Returns:
        집계된 결과
    """
    pages = get_task_pages(task_id)
    
    results = {
        "task_id": task_id,
        "pages": [],
        "total_count": len(pages)
    }
    
    for page in pages:
        # 페이지 내용 읽기
        try:
            url = f"https://api.notion.com/v1/blocks/{page['id']}/children"
            blocks_result = get(url)
            
            content = []
            for block in blocks_result.get("results", []):
                block_type = block["type"]
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = "".join(t["text"]["content"] for t in rich_text)
                if text:
                    content.append(text)
            
            results["pages"].append({
                "id": page["id"],
                "title": page["title"],
                "content": "\n".join(content)
            })
        except Exception as e:
            results["pages"].append({
                "id": page["id"],
                "title": page["title"],
                "error": str(e)
            })
    
    return results


def write_aggregated_result(
    task_id: str,
    aggregated_content: str,
    title: str = "최종 분석 결과"
) -> dict:
    """
    Task ID에 대한 최종 집계 결과를 새 페이지로 작성
    
    Args:
        task_id: Task ID
        aggregated_content: 집계된 내용
        title: 페이지 제목
        
    Returns:
        생성된 페이지 정보
    """
    return write_analysis_result(
        title=f"[최종] {title}",
        content=aggregated_content,
        metadata={"task_id": task_id},
        task_id=f"{task_id}_FINAL",
        agent_type="O-Agent"
    )
