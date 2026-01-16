"""
PRAA Notion 출력 모듈 (공통)
모든 Agent가 공유하는 Notion 페이지 작성 기능
"""
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from shared.config import get_config
from shared.notion.client import get, post, patch


def generate_task_id() -> str:
    """고유한 Task ID 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"TASK_{timestamp}_{short_uuid}"


def _get_base_page_id() -> Optional[str]:
    """Base Page ID 조회"""
    config = get_config()
    return config.notion_page_id or os.environ.get("NOTION_OUTPUT_PAGE_ID")


def _sanitize_text(text: str) -> str:
    """Notion API에서 문제가 될 수 있는 특수 문자 처리"""
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


def _split_text_to_blocks(text: str, max_length: int = 1500) -> List[str]:
    """
    긴 텍스트를 여러 블록으로 분할
    Notion API는 블록당 2000자 제한 (안전하게 1500자)
    """
    text = _sanitize_text(text)
    
    if not text:
        return []
    
    blocks = []
    lines = text.split('\n')
    current_block = ""
    
    for line in lines:
        if len(line) > max_length:
            if current_block:
                blocks.append(current_block.strip())
                current_block = ""
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
    agent_type: str = "O-Agent"
) -> Optional[Dict[str, Any]]:
    """
    Base Page 하위에 새로운 Task 페이지 생성
    
    Args:
        task_id: 고유한 Task ID
        title: 페이지 제목
        agent_type: Agent 유형
        
    Returns:
        생성된 페이지 정보 (id, url 포함)
    """
    base_page_id = _get_base_page_id()
    if not base_page_id:
        print("[Notion] ⚠️ BASE_PAGE_ID가 설정되지 않았습니다")
        return None
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    page_title = f"[{agent_type}] {title} ({task_id})"
    
    payload = {
        "parent": {"page_id": base_page_id},
        "properties": {
            "title": {"title": [{"text": {"content": page_title}}]}
        },
        "children": [
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


def append_to_page(page_id: str, blocks: list) -> Optional[Dict[str, Any]]:
    """
    기존 페이지에 블록 추가
    Notion API는 한 번에 최대 100개 블록 추가 가능
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
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


def write_analysis_result(
    title: str,
    content: str,
    metadata: dict = None,
    task_id: str = None,
    agent_type: str = "CA-Agent"
) -> Dict[str, Any]:
    """
    분석 결과를 새로운 Task 페이지에 작성
    """
    if task_id is None:
        task_id = generate_task_id()
    
    page = create_task_page(task_id=task_id, title=title, agent_type=agent_type)
    
    if not page:
        return {"status": "failed", "task_id": task_id}
    
    page_id = page.get("id")
    blocks = []
    
    # 메타데이터
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
    
    # 내용
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"text": {"content": "📊 분석 결과"}}]}
    })
    
    for block_text in _split_text_to_blocks(content):
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": block_text}}]}
        })
    
    append_to_page(page_id, blocks)
    print(f"[Notion] ✅ 분석 결과 작성 완료 (Task ID: {task_id})")
    
    return {
        "status": "success",
        "task_id": task_id,
        "page_id": page_id,
        "page_url": page.get("url")
    }


def write_qna_answer(
    question: str,
    answer: str,
    task_id: str = None,
    agent_type: str = "CA-Agent"
) -> Dict[str, Any]:
    """Q&A 결과를 새로운 Task 페이지에 작성"""
    if task_id is None:
        task_id = generate_task_id()
    
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
            "heading_3": {"rich_text": [{"text": {"content": "❓ 질문"}}]}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": question}}]}
        },
        {"object": "block", "type": "divider", "divider": {}}
    ]
    
    # 답변 블록
    answer_blocks = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"text": {"content": "💡 답변"}}]}
        }
    ]
    
    for block_text in _split_text_to_blocks(answer):
        answer_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": block_text}}]}
        })
    
    append_to_page(page_id, question_blocks + answer_blocks)
    print(f"[Notion] ✅ Q&A 결과 작성 완료 (Task ID: {task_id})")
    
    return {
        "status": "success",
        "task_id": task_id,
        "page_id": page_id,
        "page_url": page.get("url")
    }


def write_aggregated_result(
    task_id: str,
    aggregated_content: str,
    title: str = "최종 분석 결과"
) -> Dict[str, Any]:
    """Task ID에 대한 최종 집계 결과를 새 페이지로 작성"""
    return write_analysis_result(
        title=f"[최종] {title}",
        content=aggregated_content,
        metadata={"task_id": task_id},
        task_id=f"{task_id}_FINAL",
        agent_type="O-Agent"
    )
