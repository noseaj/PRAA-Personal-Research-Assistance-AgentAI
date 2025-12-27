import os
from dotenv import load_dotenv
from notion.client import post

load_dotenv()
OUTPUT_DB_ID = os.environ["NOTION_OUTPUT_DB_ID"]


def write_qna_answer(question: str, answer: str):
    payload = {
        "parent": {"database_id": OUTPUT_DB_ID},
        "properties": {
            "질의": {
                "title": [
                    {"text": {"content": question[:200]}}
                ]
            }
        },
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