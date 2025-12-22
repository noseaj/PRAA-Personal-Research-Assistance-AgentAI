"""
Agent Executor
시나리오에 따라 Agent들을 실행하고 결과를 수집
"""
from typing import Dict, Any
import sys
from pathlib import Path

# Agent wrappers import
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.r_agent_wrapper import RAgentWrapper
from agents.ca_agent_wrapper import CAAgentWrapper
from agents.sa_agent_wrapper import SAAgentWrapper


class AgentExecutor:
    """Agent 실행 조율"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: O-Agent 설정
        """
        self.config = config
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
        params = scenario_config["params"]
        
        print(f"\n{'='*60}")
        print(f"🚀 시나리오 실행: {scenario}")
        print(f"{'='*60}")
        
        results = {}
        
        if scenario == "R-only":
            results["R"] = self._execute_r(params["R"])
            
        elif scenario == "CA-only":
            results["CA"] = self._execute_ca(params["CA"])
            
        elif scenario == "SA-only":
            results["SA"] = self._execute_sa(params["SA"])
            
        elif scenario == "SA-then-R":
            # 순차 실행
            results["SA"] = self._execute_sa(params["SA"])
            # SA 결과 기반 R 쿼리 생성
            r_query = self._extract_query_from_sa(results["SA"])
            results["R"] = self._execute_r({"research_question": r_query})
            
        elif scenario == "R-then-CA":
            results["R"] = self._execute_r(params["R"])
            # R 결과에서 top paper 선택
            top_paper = self._select_top_paper(results["R"])
            ca_params = {**params["CA"]}
            if top_paper:
                ca_params["reference_paper"] = top_paper.get("title")
                ca_params["reference_github"] = self._get_first_github(top_paper)
            results["CA"] = self._execute_ca(ca_params)
            
        elif scenario == "full-pipeline":
            results["SA"] = self._execute_sa(params["SA"])
            r_query = self._extract_query_from_sa(results["SA"])
            results["R"] = self._execute_r({"research_question": r_query})
            top_paper = self._select_top_paper(results["R"])
            ca_params = {**params["CA"]}
            if top_paper:
                ca_params["reference_paper"] = top_paper.get("title")
                ca_params["reference_github"] = self._get_first_github(top_paper)
            results["CA"] = self._execute_ca(ca_params)
        
        return results
    
    def _execute_r(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """R-Agent 실행"""
        question = params.get("research_question")
        if not question:
            return {"error": "research_question이 제공되지 않았습니다"}
        return self.r_agent.run(question)
    
    def _execute_ca(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """CA-Agent 실행"""
        return self.ca_agent.run(
            user_query=params.get("user_query", ""),
            local_code_path=params.get("local_code_path"),
            reference_paper=params.get("reference_paper"),
            reference_github=params.get("reference_github")
        )
    
    def _execute_sa(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """SA-Agent 실행"""
        research_log_path = params.get("research_log_path")
        if not research_log_path:
            # 기본 경로 사용
            research_log_path = str(self.config.get("default_research_log_path"))
        return self.sa_agent.run(research_log_path)
    
    def _extract_query_from_sa(self, sa_result: Any) -> str:
        """SA 결과에서 연구 쿼리 추출"""
        # SA-Agent가 string을 반환하는 경우
        if isinstance(sa_result, str):
            # string에서 연구 주제 추출 시도
            if "DETR" in sa_result or "object detection" in sa_result.lower():
                return "DETR deformable object detection recent papers"
            elif "transformer" in sa_result.lower():
                return "transformer based models recent papers"
            else:
                return "deep learning recent papers"
        
        # dictionary인 경우
        analysis = sa_result.get("analysis", {})
        direction = analysis.get("research_direction", "")
        
        if direction and direction != "딥러닝 기반 객체 추적 연구 (Mock)":
            return direction
        
        # Mock인 경우 기본 쿼리
        return "deep learning object tracking"
    
    def _select_top_paper(self, r_result: Dict[str, Any]) -> Dict[str, Any]:
        """R-Agent 결과에서 상위 논문 선택"""
        results = r_result.get("results", [])
        if not results:
            return None
        
        # GitHub 코드가 있는 첫 번째 논문 선택
        for paper in results:
            if paper.get("code"):
                return paper
        
        # 없으면 첫 번째 논문
        return results[0]
    
    def _get_first_github(self, paper: Dict[str, Any]) -> str:
        """논문에서 첫 번째 GitHub URL 가져오기"""
        code_list = paper.get("code", [])
        if not code_list:
            return None
        return code_list[0].get("repo_url")
