"""
R-Agent Wrapper
R-Agent를 O-Agent에서 호출하기 위한 래퍼
"""
import sys
from pathlib import Path
from typing import Dict, Any

# R-Agent 경로 추가
R_AGENT_PATH = Path(__file__).parent.parent.parent / "R-Agent"
sys.path.insert(0, str(R_AGENT_PATH))

try:
    from agents.research_agent import RAgent, AgentConfig
except ImportError as e:
    print(f"[Warning] R-Agent import 실패: {e}")
    RAgent = None
    AgentConfig = None


class RAgentWrapper:
    """R-Agent 래퍼"""
    
    def __init__(self):
        """R-Agent 초기화"""
        if RAgent is None:
            self.agent = None
            print("[Warning] R-Agent를 사용할 수 없습니다")
        else:
            try:
                config = AgentConfig(output_dir=str(Path(__file__).parent.parent / "output" / "r_agent"))
                self.agent = RAgent(config)
            except Exception as e:
                print(f"[Warning] R-Agent 초기화 실패: {e}")
                self.agent = None
    
    def run(self, research_question: str) -> Dict[str, Any]:
        """
        R-Agent 실행
        
        Args:
            research_question: 연구 질문
            
        Returns:
            R-Agent 결과 (논문 + GitHub 레포 정보)
        """
        if self.agent is None:
            return self._mock_result(research_question)
        
        try:
            print(f"\n[R-Agent] 논문 검색 시작: {research_question}")
            result = self.agent.run(research_question)
            print(f"[R-Agent] 완료: {result['stats']['papers_returned']}편의 논문 발견")
            return result
        except Exception as e:
            print(f"[Error] R-Agent 실행 실패: {e}")
            return self._mock_result(research_question)
    
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
            "error": "R-Agent를 사용할 수 없습니다"
        }
    
    def format_for_display(self, result: Dict[str, Any]) -> str:
        """결과를 사람이 읽기 쉬운 형식으로 변환"""
        if not result.get("results"):
            return "논문을 찾지 못했습니다."
        
        output = []
        output.append(f"\n🔍 검색 쿼리: {', '.join(result['generated_queries'])}")
        output.append(f"📊 발견한 논문: {result['stats']['papers_returned']}편\n")
        
        for i, paper in enumerate(result["results"][:3], 1):  # 상위 3편만
            output.append(f"\n{'='*60}")
            output.append(f"📄 논문 {i}: {paper.get('title', 'N/A')}")
            output.append(f"   년도: {paper.get('year', 'N/A')}")
            output.append(f"   저자: {', '.join(paper.get('authors', [])[:3])}")
            output.append(f"   URL: {paper.get('paper_url', 'N/A')}")
            
            if paper.get("short_summary"):
                summary = paper["short_summary"]
                output.append(f"\n   문제: {summary.get('problem', 'N/A')[:100]}...")
                output.append(f"   방법: {summary.get('method', 'N/A')[:100]}...")
            
            if paper.get("code"):
                output.append(f"\n   🔗 GitHub 레포지토리:")
                for code in paper["code"][:2]:  # 상위 2개만
                    output.append(f"      - {code.get('repo_url', 'N/A')}")
                    if code.get("role_summary"):
                        output.append(f"        역할: {code['role_summary']}")
        
        return "\n".join(output)
