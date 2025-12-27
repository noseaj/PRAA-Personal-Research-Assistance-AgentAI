import pickle
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from config import LLM_CONFIG
from notion.preprocessing import LangChainChunkingEmbedding

EMBEDDING_MODEL = LLM_CONFIG["embedding_model"]

# pkl 파일 로드
def load_research_data(file_path):
    with open(file_path, 'rb') as f:
        data = pickle.load(f)
    return data

def study_agent(pkl_path):
    research_logs = load_research_data(pkl_path)

    llm = ChatOpenAI(
    model=LLM_CONFIG["model"],
    openai_api_key=LLM_CONFIG["api_key"],
    openai_api_base=LLM_CONFIG["base_url"],
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Research Agent",
    }
)
    
    system_prompt = """
    너는 숙련된 수석 연구 분석 에이전트야. 
    제공된 연구 일지 데이터를 바탕으로 프로젝트를 분석해줘.
    """
    
    # 분석 수행
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"연구 일지 분석: {research_logs}")
    ])
    
    return response.content


def save_as_text(result, filename="analysis_result.txt"):  
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(result)
        
    print(f"[OK] TXT saved: {filename}")


def save_as_json(result, pkl_path, filename="analysis_result.json"):
    data = {
        "source_file": pkl_path,
        "analysis": result,
        "metadata": {
            "model": LLM_CONFIG["model"],
            "analysis_version": "1.0"
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] JSON saved: {filename}")
    

embedding_db = study_agent("embeddings.pkl")

user_query = "특정 실험 결과는?"
processor = LangChainChunkingEmbedding(
    embedding_model = EMBEDDING_MODEL
    )

query_embedding = processor.process(user_query)


# TXT 저장
save_as_text(result, "analysis_result.txt")

# JSON 저장
save_as_json(result, "embeddings.pkl", "analysis_result.json")