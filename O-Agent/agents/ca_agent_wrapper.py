"""
CA-Agent Wrapper - subprocess로 실행
수정: 외부 파라미터 (local_code_path, reference_github, reference_paper) 전달 지원
수정: apikey.json에서 API 키 로드하여 환경 변수로 전달
"""
from typing import Optional, Dict, Any
import subprocess
import sys
import json
import os
from pathlib import Path


def load_api_keys() -> Dict[str, str]:
    """apikey.json에서 API 키 로드"""
    api_key_path = Path(__file__).parent.parent.parent / "apikey.json"
    if api_key_path.exists():
        try:
            with open(api_key_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[CA-Agent] ⚠️ apikey.json 로드 실패: {e}")
    return {}


class CAAgentWrapper:
    """CA-Agent 래퍼 - subprocess 실행 방식"""
    
    def __init__(self):
        """CA-Agent 초기화"""
        self.ca_agent_path = Path(__file__).parent.parent.parent / "CA-Agent"
        self.python_path = sys.executable
        self.api_keys = load_api_keys()
        print("[CA-Agent] ✅ Wrapper 초기화")
    
    def _get_env_with_api_keys(self) -> Dict[str, str]:
        """API 키가 포함된 환경 변수 반환"""
        env = os.environ.copy()
        
        # apikey.json의 키들을 환경 변수로 설정
        # CA-Agent가 사용하는 환경 변수명에 맞춤
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
        local_code_path: Optional[str] = None,
        reference_paper: Optional[str] = None,
        reference_github: Optional[str] = None,
        reference_paper_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CA-Agent 실행 (subprocess)
        
        Args:
            user_query: 사용자 질문
            local_code_path: 분석할 로컬 코드 경로
            reference_paper: 레퍼런스 논문 제목
            reference_github: 레퍼런스 GitHub URL (R-Agent에서 전달)
            reference_paper_text: 논문 요약 텍스트
            
        Returns:
            코드 분석 결과 딕셔너리
        """
        try:
            print(f"\n[CA-Agent] 실행 중: {user_query}")
            if local_code_path:
                print(f"[CA-Agent] 로컬 코드: {local_code_path}")
            if reference_github:
                print(f"[CA-Agent] 레퍼런스 GitHub: {reference_github}")
            if reference_paper:
                print(f"[CA-Agent] 레퍼런스 논문: {reference_paper}")
            
            # Python 스크립트 생성 - 모든 파라미터를 CA_main.py에 전달
            script = f"""
import sys
import json
sys.path.insert(0, '{self.ca_agent_path}')

try:
    from CA_main import run_pipeline
    
    # run_pipeline 실행 (외부 파라미터 전달)
    result = run_pipeline(
        user_query={repr(user_query)},
        local_code_path={repr(local_code_path) if local_code_path else 'None'},
        reference_github={repr(reference_github) if reference_github else 'None'},
        reference_paper_text={repr(reference_paper_text) if reference_paper_text else 'None'},
        reference_paper_title={repr(reference_paper) if reference_paper else 'None'}
    )
    
    # 결과 출력
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
                cwd=str(self.ca_agent_path),
                capture_output=True,
                text=True,
                timeout=300,  # 5분 타임아웃
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
                    print(f"[CA-Agent] ✅ 완료")
                else:
                    print(f"[CA-Agent] ⚠️ 실패: {parsed_result.get('error', 'Unknown error')}")
                
                return parsed_result
            
            # === ANSWER === 형태 처리 (기존 출력 형식)
            elif "=== ANSWER ===" in output:
                lines = output.split("=== ANSWER ===")
                if len(lines) > 1:
                    answer = lines[1].strip()
                    print(f"[CA-Agent] ✅ 완료")
                    return {
                        "status": "success",
                        "answer": answer,
                        "user_query": user_query,
                        "local_code_path": local_code_path,
                        "paper_name": reference_paper
                    }
            
            # 결과 없음 또는 파싱 실패
            print(f"[CA-Agent] ⚠️ 출력 파싱 실패")
            return {
                "status": "partial",
                "answer": "CA-Agent 실행 완료 (결과 파싱 실패, Notion/JSON 파일 확인 필요)",
                "stdout": output[:1000] if output else None,
                "stderr": stderr[:500] if stderr else None
            }
            
        except subprocess.TimeoutExpired:
            print(f"[CA-Agent] ❌ 타임아웃")
            return {
                "status": "failed",
                "error": "CA-Agent 타임아웃 (300초 초과)"
            }
        except Exception as e:
            print(f"[CA-Agent] ❌ 에러: {e}")
            import traceback
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def run_with_r_agent_result(
        self,
        user_query: str,
        r_agent_result: Dict[str, Any],
        local_code_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        R-Agent 결과를 사용하여 CA-Agent 실행
        """
        results = r_agent_result.get("results", [])
        
        if not results:
            return {
                "status": "failed",
                "error": "R-Agent 결과에 논문이 없습니다"
            }
        
        # 상위 논문 선택 (GitHub URL이 있는 것 우선)
        top_paper = None
        for paper in results:
            if paper.get("code"):
                top_paper = paper
                break
        
        if top_paper is None:
            top_paper = results[0]
        
        # 논문 정보 추출
        paper_title = top_paper.get("title", "Unknown")
        github_url = None
        paper_text = ""
        
        code_list = top_paper.get("code", [])
        if code_list:
            github_url = code_list[0].get("repo_url")
        
        short_summary = top_paper.get("short_summary", {})
        if short_summary:
            paper_text = f"Problem: {short_summary.get('problem', '')}\n"
            paper_text += f"Method: {short_summary.get('method', '')}\n"
            paper_text += f"Strength: {short_summary.get('strength', '')}"
        
        print(f"[CA-Agent] R-Agent → CA-Agent 파이프라인")
        print(f"[CA-Agent] 선택된 논문: {paper_title}")
        print(f"[CA-Agent] GitHub URL: {github_url}")
        
        return self.run(
            user_query=user_query,
            local_code_path=local_code_path,
            reference_paper=paper_title,
            reference_github=github_url,
            reference_paper_text=paper_text
        )
    
    def format_for_display(self, result: Dict[str, Any]) -> str:
        """결과를 사람이 읽기 쉬운 형식으로 변환"""
        if result.get("status") == "failed":
            return f"❌ CA-Agent 실패: {result.get('error', 'Unknown error')}"
        
        output = []
        output.append("\n🔍 코드 분석 결과")
        output.append("=" * 50)
        
        if result.get("paper_name"):
            output.append(f"📄 레퍼런스 논문: {result.get('paper_name')}")
        if result.get("local_code_path"):
            output.append(f"📁 분석 코드: {result.get('local_code_path')}")
        
        output.append("-" * 50)
        output.append(result.get("answer", "결과 없음"))
        output.append("=" * 50)
        
        return "\n".join(output)
