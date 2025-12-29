import os
import re
import json
from datetime import datetime

from notion.input_loader import load_tasks
from notion.output_writer import write_qna_answer
from repo.clone import clone_repo
from repo.parser import extract_functions

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
):
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

def extract_local_code_path(user_query: str):
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

def get_paper_name(reference_task):
    if not reference_task:
        return None
    return reference_task.get("title") or reference_task.get("paper_name")


# ===============================
# Reference task helpers
# ===============================

def select_reference_task(tasks, user_query: str):
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


def is_valid_reference_task(task):
    if not task:
        return False
    if not task.get("paper_text"):
        return False
    if not task.get("github"):
        return False
    return True


# ===============================
# Main pipeline
# ===============================

def run_pipeline(user_query: str):
    tasks = load_tasks()

    # ===============================
    # 1️⃣ 사용자 입력 해석
    # ===============================
    local_code_path = extract_local_code_path(user_query)
    reference_task = select_reference_task(tasks, user_query)

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
            my_functions = extract_functions(local_code_path)
            mycode_analysis = mycode_agent.run(my_functions)
        else:
            mycode_analysis = f"Local code path not found: {local_code_path}"

    # ===============================
    # 4️⃣ ReferenceAgent (조건부)
    # ===============================
    if is_valid_reference_task(reference_task):
        ref_repo_path = clone_repo(reference_task["github"])
        ref_functions = extract_functions(ref_repo_path)

        reference_analysis = reference_agent.run(
            paper_text=reference_task["paper_text"],
            functions=ref_functions,
        )

    # ===============================
    # 5️⃣ IntegrationAgent (둘 다 있을 때만)
    # ===============================
    if mycode_analysis and reference_analysis:
        integration_result = integration_agent.run(
            reference_analysis=reference_analysis,
            my_code_analysis=mycode_analysis,
        )

    # ===============================
    # 6️⃣ AnswerAgent (항상 실행)
    # ===============================
    final_answer = answer_agent.answer(
        user_query=user_query,
        reference_analysis=reference_analysis,
        my_code_analysis=mycode_analysis,
        integration_result=integration_result,
    )

    print("\n=== ANSWER ===\n")
    # print(final_answer)

    write_qna_answer(
        question=user_query,
        answer=final_answer,
    )

    paper_name = get_paper_name(reference_task)
    my_code_path = local_code_path

    json_path = write_result_json(
        paper_name=paper_name,
        my_code_path=my_code_path,
        user_query=user_query,
        answer=final_answer,
    )

    print(json_path)
    print(f"\n📄 Result JSON saved to: {json_path}")    
# ===============================
# Entry point
# ===============================

if __name__ == "__main__":
    user_query = (
        # "Paper2Code 논문 코드 설명해줘."
        "내 코드 /home/subin-oh/code/OHT_extract/UR-DMU-KD 를 분석해줘. "
        "Paper2Code 논문과 유사한 부분이 있다면 참고할 수 있는 구조를 알려줘."
    )
    run_pipeline(user_query)
