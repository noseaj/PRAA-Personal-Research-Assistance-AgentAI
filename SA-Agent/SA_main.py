import os
import re
from notion.input_loader import load_contents
from notion.output_writer import write_qna_answer
from agent.study_agent import StudyAgent


def run_pipeline(user_query):
    contents = load_contents()
    
    study_agent = StudyAgent()
    answer = study_agent.answer(user_query=user_query, content=contents)

    print("\n=== ANSWER ===\n")
    print(answer)
    
    write_qna_answer(
        question=user_query,
        answer=answer,
    )

if __name__ == "__main__":
    user_query = (
        "내 연구일지를 분석해줘. "
    )
    run_pipeline(user_query)