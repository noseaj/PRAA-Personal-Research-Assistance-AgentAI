"""
SA-Agent Wrapper - subprocess로 실행
수정: pkl_path → user_query 인터페이스 변경
수정: apikey.json에서 API 키 로드하여 환경 변수로 전달
수정: local_path 지원 추가 (로컬 연구일지 파일 분석)
"""
from typing import Optional, Dict, Any, List
import subprocess
import sys
import json
import os
import glob
from pathlib import Path
from openai import OpenAI


def load_api_keys() -> Dict[str, str]:
    """apikey.json에서 API 키 로드"""
    api_key_path = Path(__file__).parent.parent.parent / "apikey.json"
    if api_key_path.exists():
        try:
            with open(api_key_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SA-Agent] ⚠️ apikey.json 로드 실패: {e}")
    return {}


class SAAgentWrapper:
    """SA-Agent 래퍼 - subprocess 실행 방식"""
    
    def __init__(self):
        """SA-Agent 초기화"""
        self.sa_agent_path = Path(__file__).parent.parent.parent / "SA-Agent"
        self.python_path = sys.executable
        self.api_keys = load_api_keys()
        print("[SA-Agent] ✅ Wrapper 초기화")
    
    def _get_env_with_api_keys(self) -> Dict[str, str]:
        """API 키가 포함된 환경 변수 반환"""
        env = os.environ.copy()
        
        # apikey.json의 키들을 환경 변수로 설정
        if self.api_keys.get("NotionAPIKey"):
            env["NOTION_API_KEY"] = self.api_keys["NotionAPIKey"]
        
        # Notion Page ID (우선) 또는 Database ID (fallback)
        # Page 기반 방식 지원
        # NotionPageID (단일) 또는 NotionPageID_INPUT/OUTPUT (분리)
        if self.api_keys.get("NotionPageID"):
            env["NOTION_INPUT_PAGE_ID"] = self.api_keys["NotionPageID"]
            env["NOTION_OUTPUT_PAGE_ID"] = self.api_keys["NotionPageID"]
        if self.api_keys.get("NotionPageID_INPUT"):
            env["NOTION_INPUT_PAGE_ID"] = self.api_keys["NotionPageID_INPUT"]
        if self.api_keys.get("NotionPageID_OUTPUT"):
            env["NOTION_OUTPUT_PAGE_ID"] = self.api_keys["NotionPageID_OUTPUT"]
        
        # Database ID (fallback)
        if self.api_keys.get("NotionDatabaseID_INPUT"):
            env["NOTION_INPUT_DB_ID"] = self.api_keys["NotionDatabaseID_INPUT"]
        elif self.api_keys.get("NotionDatabaseID"):
            env["NOTION_INPUT_DB_ID"] = self.api_keys["NotionDatabaseID"]
        
        if self.api_keys.get("NotionDatabaseID_OUTPUT"):
            env["NOTION_OUTPUT_DB_ID"] = self.api_keys["NotionDatabaseID_OUTPUT"]
        elif self.api_keys.get("NotionDatabaseID"):
            env["NOTION_OUTPUT_DB_ID"] = self.api_keys["NotionDatabaseID"]
        
        if self.api_keys.get("OpenRouterAPIKey"):
            env["OPENROUTER_API_KEY"] = self.api_keys["OpenRouterAPIKey"]
        if self.api_keys.get("SemanticScholarAPIKey"):
            env["SEMANTIC_SCHOLAR_API_KEY"] = self.api_keys["SemanticScholarAPIKey"]
        if self.api_keys.get("GitHubToken"):
            env["GITHUB_TOKEN"] = self.api_keys["GitHubToken"]
        
        return env
    
    def run(
        self,
        user_query: str,
        local_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        SA-Agent 실행
        
        Args:
            user_query: 사용자 질문 (예: "내 연구일지를 분석해줘")
            local_path: 로컬 연구일지 경로 (선택, Notion 대신 로컬 파일 분석)
            
        Returns:
            연구 일지 분석 결과 딕셔너리
        """
        # local_path가 주어지면 로컬 파일 기반 분석
        if local_path:
            return self.run_local(user_query, local_path)
        
        # Notion 기반 분석 (기존 방식)
        return self._run_notion(user_query)
    
    def run_local(
        self,
        user_query: str,
        local_path: str
    ) -> Dict[str, Any]:
        """
        로컬 파일 기반 연구일지 분석 (LLM 사용)
        
        Args:
            user_query: 사용자 질문
            local_path: 연구일지 파일/폴더 경로
            
        Returns:
            분석 결과
        """
        try:
            print(f"\n[SA-Agent] 로컬 파일 분석: {local_path}")
            
            # 1. 로컬 파일 읽기
            content = self._read_local_files(local_path)
            if not content:
                return {
                    "status": "failed",
                    "error": f"경로에서 파일을 찾을 수 없습니다: {local_path}"
                }
            
            print(f"[SA-Agent] 📄 {len(content)}자의 연구일지 내용 로드")
            
            # 2. LLM으로 분석
            analysis = self._analyze_with_llm(user_query, content)
            
            print(f"[SA-Agent] ✅ 로컬 분석 완료")
            return {
                "status": "success",
                "answer": analysis,
                "query": user_query,
                "source": "local_files",
                "path": local_path
            }
            
        except Exception as e:
            print(f"[SA-Agent] ❌ 로컬 분석 에러: {e}")
            import traceback
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _read_local_files(self, path: str) -> str:
        """로컬 파일/폴더에서 연구일지 내용 읽기"""
        content_parts = []
        path_obj = Path(path)
        
        if path_obj.is_file():
            # 단일 파일
            try:
                with open(path_obj, 'r', encoding='utf-8') as f:
                    content_parts.append(f"## {path_obj.name}\n\n{f.read()}")
            except Exception:
                pass
        
        elif path_obj.is_dir():
            # 폴더 - .md, .txt 파일 읽기
            patterns = ['**/*.md', '**/*.txt', '**/*.log']
            
            for pattern in patterns:
                for file_path in path_obj.glob(pattern):
                    # 숨김 파일 제외
                    if any(part.startswith('.') for part in file_path.parts):
                        continue
                    # 너무 큰 파일 제외 (100KB 이상)
                    if file_path.stat().st_size > 100000:
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            relative_path = file_path.relative_to(path_obj)
                            content_parts.append(f"## 📄 {relative_path}\n\n{f.read()}\n")
                    except Exception:
                        pass
        
        # 최대 50000자로 제한
        full_content = "\n\n---\n\n".join(content_parts)
        if len(full_content) > 50000:
            full_content = full_content[:50000] + "\n\n... (내용 일부 생략)"
        
        return full_content
    
    def _analyze_with_llm(self, query: str, content: str) -> str:
        """LLM으로 연구일지 분석"""
        api_key = self.api_keys.get("OpenRouterAPIKey")
        api_url = self.api_keys.get("OpenRouterURL", "https://openrouter.ai/api/v1")
        
        if not api_key:
            return "⚠️ OpenRouter API 키가 없어 분석할 수 없습니다. apikey.json에 OpenRouterAPIKey를 추가해주세요."
        
        client = OpenAI(base_url=api_url, api_key=api_key)
        
        prompt = f"""다음은 연구일지/프로젝트 문서입니다. 사용자의 질문에 맞게 분석해주세요.

## 사용자 질문
{query}

## 연구일지 내용
{content}

## 분석 요청
위 연구일지를 분석하여 다음을 포함해 답변해주세요:
1. 주요 연구 주제 및 목표
2. 현재 진행 상황 요약
3. 주요 발견사항 또는 문제점
4. 향후 연구 방향 제안 (있다면)

한국어로 답변해주세요."""
        
        try:
            response = client.chat.completions.create(
                model="anthropic/claude-opus-4.5",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ LLM 분석 실패: {e}"
    
    def _run_notion(
        self,
        user_query: str
    ) -> Dict[str, Any]:
        """
        Notion 기반 SA-Agent 실행 (subprocess)
        
        Args:
            user_query: 사용자 질문
            
        Returns:
            연구 일지 분석 결과
        """
        try:
            print(f"\n[SA-Agent] 실행 중: {user_query}")
            
            # Python 스크립트 생성 - SA_main.py의 run_pipeline 호출
            script = f"""
import sys
import json
sys.path.insert(0, '{self.sa_agent_path}')

try:
    from SA_main import run_pipeline
    
    # run_pipeline 실행 (내부에서 Notion 연동)
    run_pipeline({repr(user_query)})
    
    # 성공 결과 출력
    result = {{
        "status": "success",
        "answer": "연구일지 분석이 완료되었습니다. Notion에서 결과를 확인하세요.",
        "query": {repr(user_query)}
    }}
    print("===RESULT_JSON_START===")
    print(json.dumps(result, ensure_ascii=False))
    print("===RESULT_JSON_END===")
    
except Exception as e:
    import traceback
    result = {{
        "status": "failed",
        "error": str(e),
        "traceback": traceback.format_exc()
    }}
    print("===RESULT_JSON_START===")
    print(json.dumps(result, ensure_ascii=False))
    print("===RESULT_JSON_END===")
"""
            
            # subprocess로 실행 (API 키 환경 변수 포함)
            result = subprocess.run(
                [self.python_path, '-c', script],
                cwd=str(self.sa_agent_path),
                capture_output=True,
                text=True,
                timeout=180,  # 3분 타임아웃
                env=self._get_env_with_api_keys()  # API 키 환경 변수 전달
            )
            
            # 결과 파싱
            output = result.stdout
            stderr = result.stderr
            
            # JSON 결과 추출
            if "===RESULT_JSON_START===" in output and "===RESULT_JSON_END===" in output:
                start = output.index("===RESULT_JSON_START===") + len("===RESULT_JSON_START===")
                end = output.index("===RESULT_JSON_END===")
                json_str = output[start:end].strip()
                parsed_result = json.loads(json_str)
                
                if parsed_result.get("status") == "success":
                    print(f"[SA-Agent] ✅ 완료")
                else:
                    print(f"[SA-Agent] ⚠️ 실패: {parsed_result.get('error', 'Unknown error')}")
                
                return parsed_result
            
            # === ANSWER === 형태 처리 (기존 SA_main.py 출력 형식)
            elif "=== ANSWER ===" in output:
                lines = output.split("=== ANSWER ===")
                if len(lines) > 1:
                    answer = lines[1].strip()
                    print(f"[SA-Agent] ✅ 완료")
                    return {
                        "status": "success",
                        "answer": answer,
                        "query": user_query
                    }
            
            # 결과 없음
            print(f"[SA-Agent] ⚠️ 출력 파싱 실패")
            return {
                "status": "partial",
                "answer": "SA-Agent 실행 완료 (Notion 확인 필요)",
                "stdout": output[:500] if output else None,
                "stderr": stderr[:500] if stderr else None
            }
            
        except subprocess.TimeoutExpired:
            print(f"[SA-Agent] ❌ 타임아웃")
            return {
                "status": "failed",
                "error": "SA-Agent 타임아웃 (180초 초과)"
            }
        except Exception as e:
            print(f"[SA-Agent] ❌ 에러: {e}")
            import traceback
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def extract_research_context(self, result: Dict[str, Any]) -> str:
        """
        SA-Agent 결과에서 연구 맥락 추출 (R-Agent 검색용)
        """
        if result.get("status") != "success":
            return ""
        
        answer = result.get("answer", "")
        
        # 간단한 키워드 추출 (향후 LLM으로 개선 가능)
        if len(answer) > 200:
            return answer[:200]
        return answer
    
    def format_for_display(self, result: Dict[str, Any]) -> str:
        """결과를 사람이 읽기 쉬운 형식으로 변환"""
        if result.get("status") == "failed":
            return f"❌ SA-Agent 실패: {result.get('error', 'Unknown error')}"
        
        output = []
        output.append("\n📔 연구 일지 분석 결과")
        output.append("=" * 50)
        output.append(result.get("answer", "결과 없음"))
        output.append("=" * 50)
        
        return "\n".join(output)
