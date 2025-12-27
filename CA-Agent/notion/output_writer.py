import os
from dotenv import load_dotenv
from notion.client import post

load_dotenv()
OUTPUT_DB_ID = os.environ["NOTION_OUTPUT_DB_ID"]


def write_qna_answer(question: str, answer: str):
    payload = {
        "parent": {"database_id": OUTPUT_DB_ID},
        "properties": {
            # ✅ DB의 title 속성 이름과 정확히 일치해야 함
            "질의": {
                "title": [
                    {"text": {"content": question[:200]}}
                ]
            }
        },
        # ✅ 나머지는 전부 페이지 본문
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": answer}}
                    ]
                }
            }
        ]
    }

    return post("https://api.notion.com/v1/pages", payload)
