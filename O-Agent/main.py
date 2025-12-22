"""
O-Agent (Orchestrator Agent) - Main Entry Point
CA, R, SA Agent를 통합 조율하는 메인 Orchestrator
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 현재 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from config import LLM_CONFIG, O_AGENT_CONFIG
from orchestrator.intent_classifier import IntentClassifier
from orchestrator.agent_executor import AgentExecutor
from orchestrator.result_synthesizer import ResultSynthesizer


class OAgent:
    """Orchestrator Agent - 통합 조율 Agent"""
    
    def __init__(self):
        """O-Agent 초기화"""
        print("\n" + "="*60)
        print("🤖 O-Agent (Orchestrator) 초기화 중...")
        print("="*60)
        
        self.llm_config = LLM_CONFIG
        self.config = O_AGENT_CONFIG
        
        # 컴포넌트 초기화
        self.classifier = IntentClassifier(self.llm_config)
        self.executor = AgentExecutor(self.config)
        self.synthesizer = ResultSynthesizer(self.llm_config)
        
        print("✅ 초기화 완료\n")
    
    def run(self, user_query: str, save_result: bool = True) -> str:
        """
        O-Agent 메인 실행 함수
        
        Args:
            user_query: 사용자 질문
            save_result: 결과를 파일로 저장할지 여부
            
        Returns:
            통합된 최종 답변
        """
        print(f"\n{'='*60}")
        print(f"📝 사용자 질문: {user_query}")
        print(f"{'='*60}\n")
        
        try:
            # 1. Intent Classification (시나리오 분류)
            print("🔍 Step 1: 의도 분석 및 시나리오 분류...")
            scenario_config = self.classifier.classify(user_query)
            print(f"   → 시나리오: {scenario_config['scenario']}")
            print(f"   → 실행할 Agent: {', '.join(scenario_config['agents'])}")
            
            # 2. Agent Execution (Agent 실행)
            print("\n🚀 Step 2: Agent 실행...")
            agent_results = self.executor.execute(scenario_config)
            
            # 3. Result Synthesis (결과 통합)
            print("\n🔄 Step 3: 결과 통합 중...")
            final_answer = self.synthesizer.synthesize(
                user_query=user_query,
                scenario=scenario_config["scenario"],
                agent_results=agent_results
            )
            
            # 4. 결과 저장 (optional)
            if save_result:
                self._save_result(
                    user_query=user_query,
                    scenario_config=scenario_config,
                    agent_results=agent_results,
                    final_answer=final_answer
                )
            
            print("\n" + "="*60)
            print("✅ O-Agent 실행 완료")
            print("="*60)
            
            return final_answer
            
        except Exception as e:
            error_msg = f"❌ O-Agent 실행 중 오류 발생: {e}"
            print(f"\n{error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg
    
    def _save_result(
        self,
        user_query: str,
        scenario_config: dict,
        agent_results: dict,
        final_answer: str
    ):
        """결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.config["output_dir"] / f"o_agent_result_{timestamp}.json"
        
        result = {
            "timestamp": timestamp,
            "user_query": user_query,
            "scenario": scenario_config["scenario"],
            "agents_used": scenario_config["agents"],
            "agent_results": agent_results,
            "final_answer": final_answer
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {output_file}")


def main():
    """메인 실행 함수"""
    # O-Agent 초기화
    o_agent = OAgent()
    
    # 예제 질문들
    examples = [
        "object tracking 관련 논문 찾아줘",
        "transformer 기반 object detection 논문 검색",
        "deep learning video understanding",
    ]
    
    print("\n" + "="*60)
    print("📚 예제 질문:")
    for i, ex in enumerate(examples, 1):
        print(f"   {i}. {ex}")
    print("="*60)
    
    # 사용자 입력 받기
    print("\n💬 질문을 입력하세요 (예제 번호 입력 또는 직접 입력):")
    user_input = input("> ").strip()
    
    # 입력 처리
    if user_input.isdigit() and 1 <= int(user_input) <= len(examples):
        query = examples[int(user_input) - 1]
    else:
        query = user_input if user_input else examples[0]
    
    # O-Agent 실행
    final_answer = o_agent.run(query)
    
    # 결과 출력
    print("\n" + "="*60)
    print("📊 최종 답변:")
    print("="*60)
    print(final_answer)
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
