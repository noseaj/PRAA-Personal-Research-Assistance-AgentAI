"""
PRAA 공통 LLM 클라이언트
OpenRouter API를 통한 다양한 LLM 모델 호출
"""
from typing import Optional, List, Dict, Any
from openai import OpenAI
from shared.config import get_config


class LLMClient:
    """
    OpenRouter 기반 LLM 클라이언트
    """
    
    # 사용 가능한 모델
    MODELS = {
        "claude-sonnet": "anthropic/claude-sonnet-4",
        "claude-opus": "anthropic/claude-opus-4.5",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "gemini-pro": "google/gemini-pro-1.5",
    }
    
    DEFAULT_MODEL = "anthropic/claude-sonnet-4"
    
    def __init__(self, model: str = None):
        """
        Args:
            model: 사용할 모델 (기본값: claude-sonnet-4)
        """
        config = get_config()
        self.client = OpenAI(
            base_url=config.openrouter_url,
            api_key=config.openrouter_api_key
        )
        
        # 모델 별칭 처리
        if model and model in self.MODELS:
            self.model = self.MODELS[model]
        else:
            self.model = model or self.DEFAULT_MODEL
    
    def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        단일 프롬프트로 LLM 호출
        
        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            temperature: 생성 온도 (0.0 ~ 1.0)
            max_tokens: 최대 토큰 수
            
        Returns:
            LLM 응답 텍스트
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content
    
    def chat_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        메시지 리스트로 LLM 호출 (멀티턴 대화)
        
        Args:
            messages: [{"role": "user/assistant/system", "content": "..."}]
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            
        Returns:
            LLM 응답 텍스트
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content
    
    def chat_json(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.1,
        **kwargs
    ) -> Optional[Dict]:
        """
        JSON 응답을 요청하는 LLM 호출
        
        Args:
            prompt: 사용자 프롬프트 (JSON 형식 요청을 포함해야 함)
            system_prompt: 시스템 프롬프트
            
        Returns:
            파싱된 JSON dict 또는 None
        """
        import json
        
        response_text = self.chat(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs
        )
        
        # JSON 블록 추출 시도
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        else:
            json_str = response_text.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None


# 편의를 위한 전역 인스턴스
_default_client = None


def get_llm_client(model: str = None) -> LLMClient:
    """LLM 클라이언트 인스턴스 반환"""
    global _default_client
    
    if model:
        return LLMClient(model)
    
    if _default_client is None:
        _default_client = LLMClient()
    
    return _default_client


def chat(prompt: str, **kwargs) -> str:
    """간편 LLM 호출 함수"""
    return get_llm_client().chat(prompt, **kwargs)
