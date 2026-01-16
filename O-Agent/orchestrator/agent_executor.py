"""
Agent Executor
시나리오에 따라 Agent들을 실행하고 결과를 수집
수정: 새로운 wrapper 인터페이스에 맞게 업데이트
"""
from typing import Dict, Any, Optional, List
import sys
import re
from pathlib import Path

# Agent wrappers import
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.r_agent_wrapper import RAgentWrapper
from agents.ca_agent_wrapper import CAAgentWrapper
from agents.sa_agent_wrapper import SAAgentWrapper


class AgentExecutor:
    """Agent 실행 조율"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: O-Agent 설정 (선택적)
        """
        self.config = config or {}
        self.r_agent = RAgentWrapper()
        self.ca_agent = CAAgentWrapper()
        self.sa_agent = SAAgentWrapper()
    
    def execute(self, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        시나리오 설정에 따라 Agent 실행
        
        Args:
            scenario_config: {
                "scenario": str,
                "agents": List[str],
                "params": Dict
            }
            
        Returns:
            각 Agent의 결과를 담은 Dictionary
        """
        scenario = scenario_config["scenario"]
        params = scenario_config.get("params", {})
        
        print(f"\n{'='*60}")
        print(f"🚀 시나리오 실행: {scenario}")
        print(f"{'='*60}")
        
        results = {}
        
        if scenario == "R-only":
            results["R"] = self._execute_r(params.get("R", {}))
            
        elif scenario == "CA-only":
            results["CA"] = self._execute_ca(params.get("CA", {}))
            
        elif scenario == "SA-only":
            results["SA"] = self._execute_sa(params.get("SA", {}))
            
        elif scenario == "SA-then-R":
            # Step 1: SA-Agent 실행
            print("\n[Step 1/2] SA-Agent 실행")
            results["SA"] = self._execute_sa(params.get("SA", {}))
            
            # Step 2: SA 결과 기반 R 쿼리 생성 후 R-Agent 실행
            print("\n[Step 2/2] R-Agent 실행 (SA 결과 기반)")
            r_query = self._extract_query_from_sa(results["SA"])
            results["R"] = self._execute_r({"research_question": r_query})
            
        elif scenario == "R-then-CA":
            # Step 1: R-Agent 실행
            print("\n[Step 1/2] R-Agent 실행")
            results["R"] = self._execute_r(params.get("R", {}))
            
            # Step 2: R 결과 기반 CA-Agent 실행
            print("\n[Step 2/2] CA-Agent 실행 (R 결과 기반)")
            ca_params = params.get("CA", {}).copy()
            top_paper = self._select_top_paper(results["R"])
            
            if top_paper:
                ca_params["reference_paper"] = top_paper.get("title")
                ca_params["reference_github"] = self._get_first_github(top_paper)
                ca_params["reference_paper_text"] = self._get_paper_summary(top_paper)
                print(f"[Agent Executor] 선택된 논문: {top_paper.get('title')}")
            
            results["CA"] = self._execute_ca(ca_params)
            
        elif scenario == "full-pipeline":
            # Step 1: SA-Agent 실행
            print("\n[Step 1/3] SA-Agent 실행")
            results["SA"] = self._execute_sa(params.get("SA", {}))
            
            # Step 2: SA 결과 기반 R-Agent 실행
            print("\n[Step 2/3] R-Agent 실행 (SA 결과 기반)")
            r_query = self._extract_query_from_sa(results["SA"])
            results["R"] = self._execute_r({"research_question": r_query})
            
            # Step 3: R 결과 기반 CA-Agent 실행
            print("\n[Step 3/3] CA-Agent 실행 (R 결과 기반)")
            ca_params = params.get("CA", {}).copy()
            top_paper = self._select_top_paper(results["R"])
            
            if top_paper:
                ca_params["reference_paper"] = top_paper.get("title")
                ca_params["reference_github"] = self._get_first_github(top_paper)
                ca_params["reference_paper_text"] = self._get_paper_summary(top_paper)
            
            results["CA"] = self._execute_ca(ca_params)
        
        else:
            print(f"[Warning] 알 수 없는 시나리오: {scenario}")
            results["error"] = f"지원하지 않는 시나리오: {scenario}"
        
        return results
    
    # ==========================================
    # 개별 Agent 실행 메서드
    # ==========================================
    
    def _execute_r(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """R-Agent 실행"""
        question = params.get("research_question") or params.get("user_query", "")
        if not question:
            return {"status": "failed", "error": "research_question이 제공되지 않았습니다"}
        
        # LLM이 추출한 영어 검색 키워드 (Optional)
        search_keywords = params.get("search_keywords", [])
        
        if search_keywords:
            print(f"[R-Agent] 검색 쿼리: {question}")
            print(f"[R-Agent] LLM 추출 키워드: {search_keywords}")
        else:
            print(f"[R-Agent] 검색 쿼리: {question}")
        
        return self.r_agent.run(question, search_keywords=search_keywords)
    
    def _execute_ca(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """CA-Agent 실행 (수정된 인터페이스)"""
        user_query = params.get("user_query", "코드를 분석해주세요")
        local_code_path = params.get("local_code_path")
        reference_paper = params.get("reference_paper")
        reference_github = params.get("reference_github")
        reference_paper_text = params.get("reference_paper_text")
        
        print(f"[CA-Agent] 쿼리: {user_query}")
        if local_code_path:
            print(f"[CA-Agent] 로컬 코드: {local_code_path}")
        if reference_github:
            print(f"[CA-Agent] 레퍼런스 GitHub: {reference_github}")
        
        return self.ca_agent.run(
            user_query=user_query,
            local_code_path=local_code_path,
            reference_paper=reference_paper,
            reference_github=reference_github,
            reference_paper_text=reference_paper_text
        )
    
    def _execute_sa(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """SA-Agent 실행 (수정된 인터페이스 - user_query 사용, local_path 지원)"""
        # user_query 우선, 없으면 기본 쿼리 사용
        user_query = params.get("user_query", "내 연구일지를 분석해주세요")
        # local_path가 있으면 로컬 파일 분석 모드
        local_path = params.get("research_log_path") or params.get("local_path")
        
        print(f"[SA-Agent] 쿼리: {user_query}")
        if local_path:
            print(f"[SA-Agent] 연구일지 경로: {local_path}")
        
        return self.sa_agent.run(user_query, local_path=local_path)
    
    # ==========================================
    # 헬퍼 메서드
    # ==========================================
    
    def _extract_query_from_sa(self, sa_result: Any) -> str:
        """SA 결과에서 연구 쿼리 추출"""
        # 새로운 SA wrapper 반환 형식 처리
        if isinstance(sa_result, dict):
            # 성공한 경우
            if sa_result.get("status") == "success":
                answer = sa_result.get("answer", "")
                return self._extract_keywords_from_text(answer)
            else:
                # 실패 시 기본 쿼리
                return "deep learning recent research"
        
        # 문자열인 경우 (이전 호환성)
        if isinstance(sa_result, str):
            return self._extract_keywords_from_text(sa_result)
        
        return "deep learning recent research"
    
    def _extract_keywords_from_text(self, text: str) -> str:
        """텍스트에서 연구 키워드 추출"""
        text_lower = text.lower()
        
        # 특정 키워드 패턴 감지
        keywords = []
        
        if "object detection" in text_lower or "객체 탐지" in text:
            keywords.append("object detection")
        if "transformer" in text_lower or "트랜스포머" in text:
            keywords.append("transformer")
        if "tracking" in text_lower or "추적" in text:
            keywords.append("tracking")
        if "segmentation" in text_lower or "분할" in text:
            keywords.append("segmentation")
        if "detr" in text_lower:
            keywords.append("DETR")
        if "yolo" in text_lower:
            keywords.append("YOLO")
        if "diffusion" in text_lower or "확산" in text:
            keywords.append("diffusion model")
        if "llm" in text_lower or "언어 모델" in text:
            keywords.append("large language model")
        if "video" in text_lower or "비디오" in text:
            keywords.append("video understanding")
        
        if keywords:
            return " ".join(keywords) + " deep learning papers"
        
        # 키워드가 없으면 첫 100자에서 명사 추출 시도
        if len(text) > 100:
            return text[:100].replace("\n", " ").strip()
        
        return "deep learning recent research papers"
    
    def _select_top_paper(self, r_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """R-Agent 결과에서 상위 논문 선택"""
        # R-Agent가 실패한 경우
        if r_result.get("status") == "failed" or r_result.get("error"):
            return None
        
        results = r_result.get("results", [])
        if not results:
            return None
        
        # GitHub 코드가 있는 첫 번째 논문 선택
        for paper in results:
            if paper.get("code"):
                return paper
        
        # 없으면 첫 번째 논문
        return results[0]
    
    def _get_first_github(self, paper: Dict[str, Any]) -> Optional[str]:
        """논문에서 첫 번째 GitHub URL 가져오기"""
        if not paper:
            return None
        code_list = paper.get("code", [])
        if not code_list:
            return None
        return code_list[0].get("repo_url")
    
    def _get_paper_summary(self, paper: Dict[str, Any]) -> str:
        """논문에서 요약 텍스트 추출"""
        if not paper:
            return ""
        
        summary_parts = []
        
        # 제목
        title = paper.get("title", "")
        if title:
            summary_parts.append(f"Title: {title}")
        
        # short_summary
        short_summary = paper.get("short_summary", {})
        if short_summary:
            if short_summary.get("problem"):
                summary_parts.append(f"Problem: {short_summary['problem']}")
            if short_summary.get("method"):
                summary_parts.append(f"Method: {short_summary['method']}")
            if short_summary.get("strength"):
                summary_parts.append(f"Strength: {short_summary['strength']}")
        
        # abstract (있는 경우)
        abstract = paper.get("abstract", "")
        if abstract:
            summary_parts.append(f"Abstract: {abstract[:500]}")
        
        return "\n".join(summary_parts)
    
    # ==========================================
    # 편의 메서드 (단일 시나리오 실행)
    # ==========================================
    
    def execute_r_only(self, research_question: str) -> Dict[str, Any]:
        """R-only 시나리오 간편 실행"""
        return self.execute({
            "scenario": "R-only",
            "params": {"R": {"research_question": research_question}}
        })
    
    def execute_sa_only(self, user_query: str = "내 연구일지를 분석해주세요") -> Dict[str, Any]:
        """SA-only 시나리오 간편 실행"""
        return self.execute({
            "scenario": "SA-only",
            "params": {"SA": {"user_query": user_query}}
        })
    
    def execute_ca_only(
        self,
        user_query: str,
        local_code_path: Optional[str] = None,
        reference_github: Optional[str] = None,
        reference_paper: Optional[str] = None
    ) -> Dict[str, Any]:
        """CA-only 시나리오 간편 실행"""
        return self.execute({
            "scenario": "CA-only",
            "params": {"CA": {
                "user_query": user_query,
                "local_code_path": local_code_path,
                "reference_github": reference_github,
                "reference_paper": reference_paper
            }}
        })
    
    def execute_r_then_ca(
        self,
        research_question: str,
        user_query: str,
        local_code_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """R-then-CA 시나리오 간편 실행"""
        return self.execute({
            "scenario": "R-then-CA",
            "params": {
                "R": {"research_question": research_question},
                "CA": {
                    "user_query": user_query,
                    "local_code_path": local_code_path
                }
            }
        })
    
    def execute_full_pipeline(
        self,
        sa_query: str,
        ca_query: str,
        local_code_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """full-pipeline 시나리오 간편 실행"""
        return self.execute({
            "scenario": "full-pipeline",
            "params": {
                "SA": {"user_query": sa_query},
                "CA": {
                    "user_query": ca_query,
                    "local_code_path": local_code_path
                }
            }
        })
