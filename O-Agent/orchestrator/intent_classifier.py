"""
Intent Classifier - LLM 기반 시나리오 분류
scenarios.md 파일을 읽고 LLM이 시나리오를 판단
"""
import json
from typing import Dict, Any
from pathlib import Path
from openai import OpenAI


class IntentClassifier:
    def __init__(self, llm_config: Dict[str, Any]):
        """
        Args:
            llm_config: LLM 설정 (api_key, base_url, model, temperature)
        """
        self.client = OpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
        )
        self.model = llm_config["model"]
        self.temperature = llm_config.get("temperature", 0.2)
        
        # 시나리오 가이드 로드
        scenarios_path = Path(__file__).parent.parent / "scenarios.md"
        with open(scenarios_path, 'r', encoding='utf-8') as f:
            self.scenarios_guide = f.read()
    
    def classify(self, user_query: str) -> Dict[str, Any]:
        """
        사용자 쿼리를 분석하여 시나리오 결정 (LLM 기반)
        
        Returns:
            {
                "scenario": "R-only" | "CA-only" | "SA-only" | "SA-then-R" | "R-then-CA" | "full-pipeline",
                "agents": ["R", "CA", "SA"],
                "reasoning": "판단 근거",
                "params": {...}
            }
        """
        print("\n" + "="*70)
        print("🔍 Intent Classification 시작 (LLM 기반)")
        print("="*70)
        print(f"📝 입력 쿼리: {user_query}")
        
        prompt = f"""아래 시나리오 가이드를 참고하여 사용자 질문에 가장 적합한 시나리오를 선택하세요.

{self.scenarios_guide}

---

사용자 질문: "{user_query}"

위 질문을 분석하여 가장 적합한 시나리오를 선택하고, JSON 형식으로 답변하세요:

{{
    "scenario": "선택한 시나리오 (R-only, CA-only, SA-only, SA-then-R, R-then-CA, full-pipeline 중 하나)",
    "reasoning": "이 시나리오를 선택한 이유 (한국어 1-2문장)",
    "confidence": 0.0~1.0 사이의 신뢰도
}}

예시:
- "object detection 논문 찾아줘" → R-only
- "PyTorch ResNet 코드 분석해줘" → CA-only  
- "내 연구 일지 분석해줘" → SA-only
- "내 연구와 관련된 논문 찾아줘" → SA-then-R
- "DETR 논문 찾고 코드 분석해줘" → R-then-CA

JSON만 출력하세요."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 추출
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            scenario = result["scenario"]
            reasoning = result.get("reasoning", "N/A")
            confidence = result.get("confidence", 0.8)
            
            print(f"\n[LLM 판단 결과]")
            print(f"   - 시나리오: {scenario}")
            print(f"   - 신뢰도: {confidence:.2f}")
            print(f"   - 근거: {reasoning}")
            print("="*70)
            
            # 시나리오에 따라 agents와 params 설정
            return self._build_scenario_config(scenario, user_query, reasoning)
            
        except Exception as e:
            print(f"\n[Warning] LLM 분류 실패: {e}")
            print("         기본 시나리오 (R-only) 사용")
            print("="*70)
            # Fallback: R-only
            return {
                "scenario": "R-only",
                "agents": ["R"],
                "reasoning": "LLM 분류 실패로 기본값 사용",
                "params": {"R": {"research_question": user_query}}
            }
    
    def _build_scenario_config(
        self, 
        scenario: str, 
        query: str,
        reasoning: str = ""
    ) -> Dict[str, Any]:
        """시나리오 설정 빌드"""
        configs = {
            "R-only": {
                "scenario": "R-only",
                "agents": ["R"],
                "reasoning": reasoning,
                "params": {"R": {"research_question": query}}
            },
            "CA-only": {
                "scenario": "CA-only",
                "agents": ["CA"],
                "reasoning": reasoning,
                "params": {"CA": {"local_code_path": None, "user_query": query}}
            },
            "SA-only": {
                "scenario": "SA-only",
                "agents": ["SA"],
                "reasoning": reasoning,
                "params": {"SA": {"research_log_path": None}}
            },
            "SA-then-R": {
                "scenario": "SA-then-R",
                "agents": ["SA", "R"],
                "reasoning": reasoning,
                "params": {
                    "SA": {"research_log_path": None},
                    "R": {"research_question": None}  # SA 결과로 채워짐
                }
            },
            "R-then-CA": {
                "scenario": "R-then-CA",
                "agents": ["R", "CA"],
                "reasoning": reasoning,
                "params": {
                    "R": {"research_question": query},
                    "CA": {"local_code_path": None, "user_query": query}
                }
            },
            "full-pipeline": {
                "scenario": "full-pipeline",
                "agents": ["SA", "R", "CA"],
                "reasoning": reasoning,
                "params": {
                    "SA": {"research_log_path": None},
                    "R": {"research_question": None},
                    "CA": {"local_code_path": None, "user_query": query}
                }
            }
        }
        
        return configs.get(scenario, configs["R-only"])
