"""
Result Synthesizer
여러 Agent의 결과를 통합하여 최종 답변 생성
"""
import json
from typing import Dict, Any
from openai import OpenAI


class ResultSynthesizer:
    """결과 통합 및 최종 답변 생성"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """
        Args:
            llm_config: LLM 설정
        """
        self.client = OpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
        )
        self.model = llm_config["model"]
        self.temperature = llm_config.get("temperature", 0.2)
    
    def synthesize(
        self,
        user_query: str,
        scenario: str,
        agent_results: Dict[str, Any]
    ) -> str:
        """
        여러 Agent 결과를 통합하여 최종 답변 생성
        
        Args:
            user_query: 사용자 질문
            scenario: 실행된 시나리오
            agent_results: 각 Agent의 결과
            
        Returns:
            통합된 최종 답변
        """
        # Agent 결과를 간결하게 요약
        summary = self._summarize_results(agent_results)
        
        prompt = f"""다음은 사용자 질문에 대한 여러 AI Agent의 분석 결과입니다.
이를 통합하여 명확하고 도움이 되는 답변을 생성하세요.

사용자 질문: {user_query}

실행된 시나리오: {scenario}

분석 결과:
{summary}

통합 답변을 다음 형식으로 작성하세요:

1. **핵심 요약**: 가장 중요한 발견 사항
2. **구체적 정보**: 
   - 논문/코드/연구 일지에서 발견된 구체적 내용
   - 추천 사항
3. **다음 단계**: 사용자가 취할 수 있는 행동

명확하고 실용적인 답변을 한국어로 작성하세요.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Warning] LLM 통합 실패, 기본 응답 사용: {e}")
            return self._fallback_synthesis(user_query, agent_results)
    
    def _summarize_results(self, agent_results: Dict[str, Any]) -> str:
        """Agent 결과를 간결하게 요약"""
        lines = []
        
        if "SA" in agent_results:
            sa = agent_results["SA"]
            lines.append("### SA-Agent (연구 일지 분석)")
            # SA-Agent도 string 또는 dict를 반환할 수 있음
            if isinstance(sa, str):
                lines.append(f"- {sa}")
            else:
                lines.append(f"- {sa.get('summary', 'N/A')}")
                if sa.get("analysis"):
                    analysis = sa["analysis"]
                    lines.append(f"- 연구 방향: {analysis.get('research_direction', 'N/A')}")
        
        if "R" in agent_results:
            r = agent_results["R"]
            lines.append("\n### R-Agent (논문 검색)")
            stats = r.get("stats", {})
            lines.append(f"- 발견한 논문: {stats.get('papers_returned', 0)}편")
            
            results = r.get("results", [])
            if results:
                lines.append("- 주요 논문:")
                for i, paper in enumerate(results[:2], 1):
                    title = paper.get("title", "N/A")
                    lines.append(f"  {i}. {title[:80]}...")
                    if paper.get("code"):
                        code = paper["code"][0]
                        lines.append(f"     GitHub: {code.get('repo_url', 'N/A')}")
        
        if "CA" in agent_results:
            ca = agent_results["CA"]
            lines.append("\n### CA-Agent (코드 분석)")
            # CA-Agent는 string 또는 dict를 반환할 수 있음
            if isinstance(ca, str):
                lines.append(f"- {ca}")
            else:
                lines.append(f"- {ca.get('final_answer', 'N/A')}")
        
        return "\n".join(lines)
    
    def _fallback_synthesis(
        self,
        user_query: str,
        agent_results: Dict[str, Any]
    ) -> str:
        """Fallback: LLM 없이도 기본 통합 답변 생성"""
        output = []
        output.append(f"질문: {user_query}\n")
        output.append("=" * 60)
        
        if "SA" in agent_results:
            output.append("\n📚 연구 일지 분석:")
            output.append(agent_results["SA"].get("summary", "N/A"))
        
        if "R" in agent_results:
            output.append("\n\n🔍 논문 검색 결과:")
            r = agent_results["R"]
            stats = r.get("stats", {})
            output.append(f"발견한 논문: {stats.get('papers_returned', 0)}편")
            
            results = r.get("results", [])
            if results:
                for i, paper in enumerate(results[:3], 1):
                    output.append(f"\n{i}. {paper.get('title', 'N/A')}")
                    if paper.get("code"):
                        code = paper["code"][0]
                        output.append(f"   GitHub: {code.get('repo_url', 'N/A')}")
        
        if "CA" in agent_results:
            output.append("\n\n💻 코드 분석:")
            ca = agent_results["CA"]
            if isinstance(ca, str):
                output.append(ca)
            else:
                output.append(ca.get("final_answer", "N/A"))
        
        output.append("\n" + "=" * 60)
        output.append("\n💡 다음 단계:")
        output.append("1. 추천된 논문을 검토하세요")
        output.append("2. GitHub 레포지토리를 탐색하세요")
        output.append("3. 코드 분석 결과를 참고하여 구현하세요")
        
        return "\n".join(output)
