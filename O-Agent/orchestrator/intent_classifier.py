"""
Intent Classifier
OpenRouter LLM을 사용하여 사용자 질문을 분석하고 적절한 시나리오 결정
"""
import json
import re
from typing import Dict, Any
from openai import OpenAI


class IntentClassifier:
    """사용자 질문을 분석하여 시나리오 결정"""
    
    def __init__(self, openrouter_api_key: str, openrouter_url: str):
        """
        Args:
            openrouter_api_key: OpenRouter API Key
            openrouter_url: OpenRouter API URL
        """
        self.client = OpenAI(
            base_url=openrouter_url,
            api_key=openrouter_api_key
        )
        self.model = "anthropic/claude-sonnet-4"  # 고성능 모델
    
    def classify(self, user_query: str) -> Dict[str, Any]:
        """
        사용자 질문을 분석하여 시나리오 결정
        
        Args:
            user_query: 사용자 질문
            
        Returns:
            {
                "scenario": "R-only",
                "agents": ["R-Agent"],
                "reasoning": "...",
                "confidence": 0.95,
                "extracted_info": {...}
            }
        """
        
        # LLM에게 질문 분석 요청
        prompt = self._build_classification_prompt(user_query)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 사용자 질문을 분석하여 적절한 AI Agent 시나리오를 결정하는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 추출
            result = self._extract_json(result_text)
            
            # scenario에서 agents 목록 생성
            result["agents"] = self.get_agent_list(result.get("scenario", "R-only"))
            
            # 추가 정보 추출 (경로, 논문명 등)
            result["extracted_info"] = self._extract_additional_info(user_query)
            
            return result
            
        except Exception as e:
            print(f"[Intent Classifier] LLM 호출 실패: {e}")
            # 기본값 반환 (규칙 기반)
            return self._fallback_classification(user_query)
    
    def _build_classification_prompt(self, user_query: str) -> str:
        """분류 프롬프트 생성 - 검색 키워드도 함께 추출"""
        return f"""다음 사용자 질문을 분석하여 가장 적합한 Agent 시나리오를 선택하세요.

**사용 가능한 Agent:**
- R-Agent: 논문 검색 및 GitHub 레포지토리 찾기
- SA-Agent: 연구 일지 분석
- CA-Agent: 코드 분석 및 논문 코드 비교

**시나리오 옵션:**
1. "R-only": 논문만 검색
   - 예: "object detection 논문 찾아줘"
   
2. "SA-only": 연구 일지만 분석
   - 예: "내 연구 일지를 분석해줘"
   
3. "CA-only": 코드만 분석
   - 예: "내 코드를 분석해줘", "/path/to/code 분석해줘"
   
4. "R-then-CA": 논문 검색 → 코드 분석
   - 예: "DETR 논문 찾고 코드 분석해줘", "object detection 논문 찾아서 내 코드와 비교해줘"
   
5. "SA-then-R": 연구 일지 분석 → 관련 논문 검색
   - 예: "내 연구와 관련된 논문 찾아줘"

---

**사용자 질문:** "{user_query}"

위 질문을 분석하여 JSON 형식으로 답변하세요:

{{
    "scenario": "선택한 시나리오",
    "reasoning": "이 시나리오를 선택한 이유 (한국어 1-2문장)",
    "confidence": 0.0~1.0 사이의 신뢰도,
    "search_keywords": ["영어", "키워드", "목록"] (R-Agent 사용 시 필수! Semantic Scholar 검색용 영어 키워드 3-5개)
}}

**중요:**
- search_keywords는 반드시 **영어**로 작성! (예: "DETR", "object detection", "transformer")
- 사용자가 한글로 질문해도 영어 학술 키워드로 변환하세요
- 유명 논문/모델명(DETR, ResNet, BERT 등)은 원래 이름 그대로 포함

JSON만 출력하세요."""
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """텍스트에서 JSON 추출"""
        # JSON 블록 찾기
        json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # 기본값
        return {
            "scenario": "R-only",
            "reasoning": "JSON 파싱 실패, 기본 시나리오 사용",
            "confidence": 0.5
        }
    
    def _extract_additional_info(self, user_query: str) -> Dict[str, Any]:
        """사용자 질문에서 추가 정보 추출 (경로, 논문명 등)"""
        info = {
            "local_code_path": None,
            "paper_keywords": [],
        }
        
        # 경로 추출 (Linux/macOS/Windows)
        path_patterns = [
            r"(/[\w\-/\.]+)",  # Linux/macOS
            r"([A-Za-z]:\\[^\s]+)",  # Windows
            r"(~/[\w\-/\.]+)",  # Home directory
        ]
        
        for pattern in path_patterns:
            match = re.search(pattern, user_query)
            if match:
                info["local_code_path"] = match.group(1)
                break
        
        # 논문 키워드 추출 (간단한 규칙)
        # "DETR", "ResNet" 같은 대문자로 시작하는 단어
        paper_keywords = re.findall(r'\b[A-Z][A-Za-z0-9]+\b', user_query)
        if paper_keywords:
            info["paper_keywords"] = paper_keywords
        
        return info
    
    def _fallback_classification(self, user_query: str) -> Dict[str, Any]:
        """LLM 실패 시 규칙 기반 분류"""
        query_lower = user_query.lower()
        
        # 연구 일지 관련
        if any(keyword in query_lower for keyword in ["연구일지", "연구 일지", "내 연구"]):
            if any(keyword in query_lower for keyword in ["논문", "paper", "찾"]):
                return {
                    "scenario": "SA-then-R",
                    "agents": ["SA-Agent", "R-Agent"],
                    "reasoning": "연구 일지 기반 논문 검색",
                    "confidence": 0.7,
                    "extracted_info": self._extract_additional_info(user_query)
                }
            else:
                return {
                    "scenario": "SA-only",
                    "agents": ["SA-Agent"],
                    "reasoning": "연구 일지 분석",
                    "confidence": 0.8,
                    "extracted_info": self._extract_additional_info(user_query)
                }
        
        # 코드 분석 관련
        if any(keyword in query_lower for keyword in ["코드", "code", "분석", "경로", "/"]):
            if any(keyword in query_lower for keyword in ["논문", "paper"]):
                return {
                    "scenario": "R-then-CA",
                    "agents": ["R-Agent", "CA-Agent"],
                    "reasoning": "논문 찾고 코드 비교",
                    "confidence": 0.75,
                    "extracted_info": self._extract_additional_info(user_query)
                }
            else:
                return {
                    "scenario": "CA-only",
                    "agents": ["CA-Agent"],
                    "reasoning": "코드 분석",
                    "confidence": 0.7,
                    "extracted_info": self._extract_additional_info(user_query)
                }
        
        # 기본값: 논문 검색
        return {
            "scenario": "R-only",
            "agents": ["R-Agent"],
            "reasoning": "논문 검색",
            "confidence": 0.6,
            "extracted_info": self._extract_additional_info(user_query)
        }
    
    def get_agent_list(self, scenario: str) -> list[str]:
        """시나리오에서 필요한 Agent 목록 반환"""
        scenario_map = {
            "R-only": ["R-Agent"],
            "SA-only": ["SA-Agent"],
            "CA-only": ["CA-Agent"],
            "R-then-CA": ["R-Agent", "CA-Agent"],
            "SA-then-R": ["SA-Agent", "R-Agent"],
            "full-pipeline": ["SA-Agent", "R-Agent", "CA-Agent"],
        }
        return scenario_map.get(scenario, ["R-Agent"])
