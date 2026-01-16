"""
R-Agent Wrapper
R-Agent를 O-Agent에서 호출하기 위한 래퍼
수정: subprocess 기반으로 변경하여 import 문제 해결
"""
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional


class RAgentWrapper:
    """R-Agent 래퍼 - subprocess 실행 방식"""
    
    def __init__(self):
        """R-Agent 초기화"""
        self.r_agent_path = Path(__file__).parent.parent.parent / "R-Agent"
        self.python_path = sys.executable
        self.available = True
        
        # R-Agent 경로 확인
        if not (self.r_agent_path / "agents" / "research_agent.py").exists():
            print("[Warning] R-Agent 파일을 찾을 수 없습니다")
            self.available = False
        else:
            print("[R-Agent] ✅ Wrapper 초기화")
    
    def run(self, research_question: str, search_keywords: list = None) -> Dict[str, Any]:
        """
        R-Agent 실행 (subprocess)
        
        Args:
            research_question: 연구 질문
            search_keywords: LLM이 추출한 영어 검색 키워드 목록 (Optional)
            
        Returns:
            R-Agent 결과 (논문 + GitHub 레포 정보)
        """
        if not self.available:
            return self._mock_result(research_question)
        
        try:
            # 키워드가 있으면 키워드 사용, 없으면 원본 질문 사용
            if search_keywords and len(search_keywords) > 0:
                search_query = " ".join(search_keywords)
                print(f"\n[R-Agent] 논문 검색 시작 (키워드: {search_keywords})")
            else:
                search_query = research_question
                print(f"\n[R-Agent] 논문 검색 시작: {research_question}")
            
            # 쿼리 이스케이프
            escaped_query = search_query.replace("'", "\\'").replace('"', '\\"')
            keywords_json = json.dumps(search_keywords or [], ensure_ascii=False)
            
            # subprocess로 R-Agent 실행
            script = f"""
import sys
import json
sys.path.insert(0, '{self.r_agent_path}')

try:
    from agents.research_agent import RAgent, AgentConfig
    
    cfg = AgentConfig(output_dir='{self.r_agent_path}/output')
    agent = RAgent(cfg)
    
    # 외부에서 전달받은 키워드 사용
    keywords = {keywords_json}
    result = agent.run('{escaped_query}', external_keywords=keywords if keywords else None)
    
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
            
            result = subprocess.run(
                [self.python_path, '-c', script],
                cwd=str(self.r_agent_path),
                capture_output=True,
                text=True,
                timeout=180  # 3분 타임아웃
            )
            
            output = result.stdout
            stderr = result.stderr
            
            # JSON 결과 추출
            if "===RESULT_JSON_START===" in output and "===RESULT_JSON_END===" in output:
                start = output.index("===RESULT_JSON_START===") + len("===RESULT_JSON_START===")
                end = output.index("===RESULT_JSON_END===")
                json_str = output[start:end].strip()
                parsed_result = json.loads(json_str)
                
                if "status" in parsed_result and parsed_result["status"] == "failed":
                    print(f"[R-Agent] ❌ 실패: {parsed_result.get('error')}")
                else:
                    papers_count = parsed_result.get("stats", {}).get("papers_returned", 0)
                    print(f"[R-Agent] ✅ 완료: {papers_count}편의 논문 발견")
                
                return parsed_result
            
            # 파싱 실패
            print(f"[R-Agent] ⚠️ 출력 파싱 실패")
            if stderr:
                print(f"[R-Agent] stderr: {stderr[:500]}")
            
            return {
                "status": "failed",
                "error": "결과 파싱 실패",
                "stdout": output[:500] if output else None,
                "stderr": stderr[:500] if stderr else None
            }
            
        except subprocess.TimeoutExpired:
            print(f"[R-Agent] ❌ 타임아웃")
            return {
                "status": "failed",
                "error": "R-Agent 타임아웃 (180초 초과)"
            }
        except Exception as e:
            print(f"[R-Agent] ❌ 에러: {e}")
            import traceback
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _mock_result(self, question: str) -> Dict[str, Any]:
        """Mock 결과 (R-Agent를 사용할 수 없을 때)"""
        return {
            "agent": "R-Agent (Mock)",
            "input_question": question,
            "generated_queries": [question],
            "results": [],
            "stats": {
                "candidates_collected": 0,
                "papers_returned": 0,
                "repos_analyzed": 0,
            },
            "status": "failed",
            "error": "R-Agent를 사용할 수 없습니다"
        }
    
    def format_for_display(self, result: Dict[str, Any]) -> str:
        """결과를 사람이 읽기 쉬운 형식으로 변환"""
        if result.get("status") == "failed":
            return f"❌ R-Agent 실패: {result.get('error', 'Unknown')}"
        
        if not result.get("results"):
            return "논문을 찾지 못했습니다."
        
        output = []
        output.append(f"\n🔍 검색 쿼리: {', '.join(result.get('generated_queries', []))}")
        output.append(f"📊 발견한 논문: {result.get('stats', {}).get('papers_returned', 0)}편\n")
        
        for i, paper in enumerate(result["results"][:3], 1):  # 상위 3편만
            output.append(f"\n{'='*60}")
            output.append(f"📄 논문 {i}: {paper.get('title', 'N/A')}")
            output.append(f"   년도: {paper.get('year', 'N/A')}")
            authors = paper.get('authors', [])
            if authors:
                output.append(f"   저자: {', '.join(authors[:3])}")
            output.append(f"   URL: {paper.get('paper_url', 'N/A')}")
            
            if paper.get("short_summary"):
                summary = paper["short_summary"]
                if summary.get('problem'):
                    output.append(f"\n   문제: {summary['problem'][:100]}...")
                if summary.get('method'):
                    output.append(f"   방법: {summary['method'][:100]}...")
            
            if paper.get("code"):
                output.append(f"\n   🔗 GitHub 레포지토리:")
                for code in paper["code"][:2]:  # 상위 2개만
                    output.append(f"      - {code.get('repo_url', 'N/A')}")
                    if code.get("role_summary"):
                        output.append(f"        역할: {code['role_summary']}")
        
        return "\n".join(output)
