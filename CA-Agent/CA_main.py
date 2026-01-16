"""
CA-Agent Main Pipeline
수정: 외부 파라미터 (local_code_path, reference_github, reference_paper_text) 지원
리팩토링: shared 모듈 사용
"""
import sys
import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# shared 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import get_config
from shared.notion.writer import write_qna_answer

# CA-Agent 내부 모듈
from repo.clone import clone_repo
from repo.parser import extract_functions

# Notion input_loader (기존 로직 유지)
try:
    from notion.input_loader import load_tasks
except ImportError:
    def load_tasks():
        return []

from agents.reference_agent import ReferenceAgent
from agents.mycode_agent import MyCodeAgent
from agents.integration_agent import IntegrationAgent
from agents.answer_agent import AnswerAgent


# ===============================
# Answer Output
# ===============================
def write_result_json(
    paper_name: str,
    my_code_path: str,
    user_query: str,
    answer: str,
    output_dir: str = "CA-outputs"
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"analysis_result_{timestamp}.json")

    result = {
        "paper_name": paper_name,
        "my_code_path": my_code_path,
        "user_query": user_query,
        "answer": answer,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return output_path


# ===============================
# User query helpers
# ===============================

def extract_local_code_path(user_query: str) -> Optional[str]:
    """
    user_query에서 로컬 코드 경로 추출
    """
    # Linux / macOS / WSL
    match = re.search(r"(/[\w\-/\.]+)", user_query)
    if match:
        return match.group(1)

    # Windows
    match = re.search(r"([A-Za-z]:\\[^\s]+)", user_query)
    if match:
        return match.group(1)

    return None


# ===============================
# Task name
# ===============================

def get_paper_name(reference_task: Optional[Dict]) -> Optional[str]:
    if not reference_task:
        return None
    return reference_task.get("title") or reference_task.get("paper_name")


# ===============================
# Reference task helpers
# ===============================

def select_reference_task(tasks, user_query: str) -> Optional[Dict]:
    """
    Notion task 중 user_query와 가장 관련된 paper 선택
    """
    query = user_query.lower()

    for task in tasks:
        title = task.get("title", "").lower()
        github = task.get("github", "")

        if title and title in query:
            return task
        if github and github in query:
            return task

    return None


def is_valid_reference_task(task: Optional[Dict]) -> bool:
    if not task:
        return False
    if not task.get("paper_text"):
        return False
    if not task.get("github"):
        return False
    return True


def create_external_reference_task(
    reference_github: str,
    reference_paper_text: Optional[str] = None,
    reference_paper_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    외부에서 전달된 파라미터로 reference_task 생성
    (O-Agent/R-Agent에서 전달받은 경우)
    """
    return {
        "title": reference_paper_title or "External Reference",
        "github": reference_github,
        "paper_text": reference_paper_text or "",
    }


# ===============================
# Main pipeline
# ===============================

def run_pipeline(
    user_query: str,
    local_code_path: Optional[str] = None,
    reference_github: Optional[str] = None,
    reference_paper_text: Optional[str] = None,
    reference_paper_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    CA-Agent 파이프라인 실행
    
    Args:
        user_query: 사용자 질문
        local_code_path: 분석할 로컬 코드 경로 (외부에서 전달 가능)
        reference_github: 레퍼런스 GitHub URL (O-Agent/R-Agent에서 전달)
        reference_paper_text: 논문 텍스트 (O-Agent/R-Agent에서 전달)
        reference_paper_title: 논문 제목 (O-Agent/R-Agent에서 전달)
        
    Returns:
        분석 결과 딕셔너리
    """
    
    # ===============================
    # 0️⃣ Notion에서 기존 Tasks 로드 (fallback용)
    # ===============================
    try:
        tasks = load_tasks()
    except Exception as e:
        print(f"[Warning] Notion tasks 로드 실패: {e}")
        tasks = []

    # ===============================
    # 1️⃣ 사용자 입력 해석
    # ===============================
    
    # local_code_path 결정
    # 우선순위: 1) 외부 파라미터 2) user_query에서 추출
    if local_code_path is None:
        local_code_path = extract_local_code_path(user_query)
    
    # reference_task 결정
    # 우선순위: 1) 외부 파라미터 (R-Agent 결과) 2) Notion에서 검색
    reference_task = None
    
    if reference_github:
        # 외부에서 GitHub URL이 전달된 경우 (R-Agent → CA-Agent 파이프라인)
        print(f"[CA-Agent] 외부 레퍼런스 사용: {reference_github}")
        reference_task = create_external_reference_task(
            reference_github=reference_github,
            reference_paper_text=reference_paper_text,
            reference_paper_title=reference_paper_title
        )
    else:
        # Notion에서 검색 (기존 동작)
        reference_task = select_reference_task(tasks, user_query)
        if reference_task:
            print(f"[CA-Agent] Notion 레퍼런스 사용: {reference_task.get('title')}")

    print(f"[CA-Agent] local_code_path: {local_code_path}")
    print(f"[CA-Agent] reference_task: {get_paper_name(reference_task)}")

    # ===============================
    # 2️⃣ Agents 초기화
    # ===============================
    mycode_agent = MyCodeAgent()
    reference_agent = ReferenceAgent()
    integration_agent = IntegrationAgent()
    answer_agent = AnswerAgent()

    mycode_analysis = None
    reference_analysis = None
    integration_result = None

    # ===============================
    # 3️⃣ MyCodeAgent (조건부)
    # ===============================
    if local_code_path:
        if os.path.exists(local_code_path):
            print(f"[CA-Agent] MyCodeAgent 실행 중...")
            my_functions = extract_functions(local_code_path)
            mycode_analysis = mycode_agent.run(my_functions)
            print(f"[CA-Agent] MyCodeAgent 완료")
        else:
            mycode_analysis = f"Local code path not found: {local_code_path}"
            print(f"[CA-Agent] ⚠️ 로컬 코드 경로를 찾을 수 없음: {local_code_path}")

    # ===============================
    # 4️⃣ ReferenceAgent (조건부)
    # ===============================
    if reference_task:
        github_url = reference_task.get("github")
        paper_text = reference_task.get("paper_text", "")
        
        if github_url:
            print(f"[CA-Agent] ReferenceAgent 실행 중... (GitHub: {github_url})")
            try:
                ref_repo_path = clone_repo(github_url)
                ref_functions = extract_functions(ref_repo_path)
                
                reference_analysis = reference_agent.run(
                    paper_text=paper_text,
                    functions=ref_functions,
                )
                print(f"[CA-Agent] ReferenceAgent 완료")
            except Exception as e:
                print(f"[CA-Agent] ⚠️ ReferenceAgent 실패: {e}")
                reference_analysis = f"레퍼런스 분석 실패: {str(e)}"
        else:
            print(f"[CA-Agent] ⚠️ GitHub URL이 없어서 ReferenceAgent 스킵")
    else:
        print(f"[CA-Agent] ℹ️ 레퍼런스가 없어서 ReferenceAgent 스킵")

    # ===============================
    # 5️⃣ IntegrationAgent (둘 다 있을 때만)
    # ===============================
    if mycode_analysis and reference_analysis and not isinstance(mycode_analysis, str) and not isinstance(reference_analysis, str):
        print(f"[CA-Agent] IntegrationAgent 실행 중...")
        integration_result = integration_agent.run(
            reference_analysis=reference_analysis,
            my_code_analysis=mycode_analysis,
        )
        print(f"[CA-Agent] IntegrationAgent 완료")
    elif mycode_analysis and reference_analysis:
        # 하나라도 에러 문자열인 경우
        integration_result = None
        print(f"[CA-Agent] ℹ️ IntegrationAgent 스킵 (분석 결과 부족)")

    # ===============================
    # 6️⃣ AnswerAgent (항상 실행)
    # ===============================
    print(f"[CA-Agent] AnswerAgent 실행 중...")
    final_answer = answer_agent.answer(
        user_query=user_query,
        reference_analysis=reference_analysis,
        my_code_analysis=mycode_analysis,
        integration_result=integration_result,
    )
    print(f"[CA-Agent] AnswerAgent 완료")

    print("\n=== ANSWER ===\n")
    # print(final_answer)

    # Notion 기록은 O-Agent에서 일괄 처리
    # (중복 기록 방지를 위해 CA-Agent에서는 기록하지 않음)

    # JSON 파일로 저장
    paper_name = get_paper_name(reference_task)
    json_path = write_result_json(
        paper_name=paper_name,
        my_code_path=local_code_path,
        user_query=user_query,
        answer=final_answer,
    )

    print(f"\n📄 Result JSON saved to: {json_path}")
    
    # 결과 반환
    return {
        "status": "success",
        "answer": final_answer,
        "paper_name": paper_name,
        "local_code_path": local_code_path,
        "json_path": json_path,
        "has_mycode_analysis": mycode_analysis is not None,
        "has_reference_analysis": reference_analysis is not None,
        "has_integration": integration_result is not None
    }


# ===============================
# Entry point
# ===============================

if __name__ == "__main__":
    # 테스트 1: 기존 방식 (user_query에 모든 정보 포함)
    user_query = (
        "내 코드 /home/subin-oh/code/OHT_extract/UR-DMU-KD 를 분석해줘. "
        "Paper2Code 논문과 유사한 부분이 있다면 참고할 수 있는 구조를 알려줘."
    )
    # run_pipeline(user_query)
    
    # 테스트 2: 새로운 방식 (외부 파라미터 전달)
    result = run_pipeline(
        user_query="내 코드를 DETR 논문과 비교 분석해줘",
        local_code_path="/home/subin-oh/code/OHT_extract/UR-DMU-KD",
        reference_github="https://github.com/facebookresearch/detr",
        reference_paper_text="DETR: End-to-End Object Detection with Transformers",
        reference_paper_title="DETR"
    )
    print(f"\n결과: {result}")
