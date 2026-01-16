#!/usr/bin/env python3
"""
PRAA O-Agent 자동 실행 스크립트
자연어 질문을 자동으로 분석하여 적절한 시나리오 판별 및 실행
Task ID 기반 Notion 연동 및 결과 집계 기능 포함

사용법:
    python auto_agent.py "논문 찾아줘"                          # R-only
    python auto_agent.py "내 연구일지 분석해줘"                  # SA-only  
    python auto_agent.py "DETR 논문 찾아서 코드 분석해줘"       # R-then-CA
    python auto_agent.py --local-path /path/to/code "코드 분석" # CA-only with path
"""
import sys
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 프로젝트 루트 경로 추가 (shared 모듈 import용)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

# shared 모듈 사용
from shared.config import get_config, Config
from shared.notion.writer import generate_task_id

from orchestrator.agent_executor import AgentExecutor


class NotionWriter:
    """Notion에 결과를 기록하는 헬퍼 클래스"""
    
    def __init__(self):
        """초기화 - shared.config 사용"""
        self.config = get_config()
        self.enabled = self._setup_env()
    
    def _setup_env(self) -> bool:
        """환경 변수 설정 및 Notion 연동 가능 여부 확인"""
        self.config.setup_notion_env()
        return bool(self.config.notion_api_key and self.config.notion_page_id)
    
    def write_result(
        self,
        task_id: str,
        agent_type: str,
        title: str,
        content: str,
        metadata: dict = None
    ) -> dict:
        """결과를 Notion에 기록"""
        if not self.enabled:
            return {"status": "skipped", "reason": "Notion not configured"}
        
        try:
            # shared/notion/writer 사용 (리팩토링)
            from shared.notion.writer import write_analysis_result
            
            return write_analysis_result(
                title=title,
                content=content,
                metadata=metadata,
                task_id=task_id,
                agent_type=agent_type
            )
        except Exception as e:
            print(f"[Notion] ⚠️ 기록 실패: {e}")
            return {"status": "failed", "error": str(e)}
    
    def write_aggregated_result(
        self,
        task_id: str,
        user_query: str,
        results: Dict[str, Any]
    ) -> dict:
        """최종 집계 결과를 Notion에 기록 (LLM 요약 포함)"""
        if not self.enabled:
            return {"status": "skipped", "reason": "Notion not configured"}
        
        # LLM으로 결과 요약 생성
        aggregated_content = self._format_aggregated_result_with_llm(user_query, results)
        
        try:
            from shared.notion.writer import write_aggregated_result
            
            return write_aggregated_result(
                task_id=task_id,
                aggregated_content=aggregated_content,
                title=f"분석 결과: {user_query[:30]}..."
            )
        except Exception as e:
            print(f"[Notion] ⚠️ 집계 결과 기록 실패: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _format_aggregated_result_with_llm(
        self,
        user_query: str,
        results: Dict[str, Any]
    ) -> str:
        """LLM을 사용하여 여러 Agent 결과를 통합 요약"""
        # 먼저 원본 데이터 포맷팅
        raw_content = self._format_raw_results(user_query, results)
        
        # LLM으로 요약 시도 (shared.config 사용)
        api_key = self.config.openrouter_api_key
        api_url = self.config.openrouter_url
        
        if not api_key:
            # LLM 없으면 원본 반환
            return raw_content
        
        try:
            from openai import OpenAI
            client = OpenAI(base_url=api_url, api_key=api_key)
            
            prompt = f"""다음은 여러 AI Agent들의 분석 결과입니다. 이를 하나의 통합 보고서로 요약해주세요.

## 사용자 질문
{user_query}

## Agent별 원본 결과
{raw_content}

## 요청
위 결과들을 통합하여 사용자가 이해하기 쉬운 형태로 정리해주세요.
포함해야 할 내용:
1. 질문에 대한 핵심 답변 (2-3문장)
2. 주요 발견 사항 (논문, 코드, 연구 인사이트 등)
3. 추가 제안 또는 다음 단계

형식: 마크다운으로 작성
언어: 한국어"""
            
            response = client.chat.completions.create(
                model="anthropic/claude-opus-4.5",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            
            llm_summary = response.choices[0].message.content
            
            # LLM 요약 + 원본 데이터 결합
            return f"""# 📊 통합 분석 보고서

## 🎯 질문
{user_query}

---

## 📝 요약
{llm_summary}

---

## 📋 상세 결과 (Agent별)
{raw_content}
"""
        except Exception as e:
            print(f"[Notion] ⚠️ LLM 요약 실패, 원본 사용: {e}")
            return raw_content
    
    def _format_raw_results(
        self,
        user_query: str,
        results: Dict[str, Any]
    ) -> str:
        """원본 결과를 포맷팅"""
        lines = []
        
        for agent_name, result in results.items():
            if agent_name == "error":
                continue
            
            lines.append(f"### 🤖 {agent_name}\n")
            
            if isinstance(result, dict):
                status = result.get("status", "unknown")
                
                if status == "success":
                    lines.append("**상태:** ✅ 성공\n")
                elif status == "failed":
                    lines.append(f"**상태:** ❌ 실패 - {result.get('error', '')}\n")
                else:
                    lines.append(f"**상태:** {status}\n")
                
                # R-Agent 논문 결과
                if result.get("results"):
                    papers = result["results"]
                    lines.append(f"\n**발견 논문:** {len(papers)}편\n")
                    for i, paper in enumerate(papers[:5], 1):
                        title = paper.get("title", "N/A")
                        year = paper.get("year", "N/A")
                        code = paper.get("code", [])
                        github = code[0].get("repo_url") if code else "N/A"
                        lines.append(f"- **[{i}] {title}** ({year})\n")
                        if github != "N/A":
                            lines.append(f"  - GitHub: {github}\n")
                
                # 답변
                if result.get("answer"):
                    answer = result["answer"]
                    lines.append(f"\n**분석 결과:**\n{answer}\n")
            
            lines.append("\n")
        
        return "".join(lines)


class AutoIntentClassifier:
    """
    API 키 없이도 동작하는 규칙 기반 Intent Classifier
    (LLM 기반 classifier가 실패하면 fallback으로 사용)
    """
    
    def __init__(self, use_llm: bool = False, api_key: str = None, api_url: str = None):
        """
        Args:
            use_llm: LLM 사용 여부 (True면 OpenRouter 사용)
            api_key: OpenRouter API Key
            api_url: OpenRouter API URL
        """
        self.use_llm = use_llm
        self.llm_classifier = None
        
        # LLM 사용 시 IntentClassifier 초기화
        if use_llm and api_key and api_url:
            try:
                from orchestrator.intent_classifier import IntentClassifier
                self.llm_classifier = IntentClassifier(api_key, api_url)
                print("[Intent Classifier] ✅ LLM 기반 분류기 초기화")
            except Exception as e:
                print(f"[Intent Classifier] ⚠️ LLM 초기화 실패, 규칙 기반 사용: {e}")
    
    def classify(self, user_query: str) -> Dict[str, Any]:
        """자연어 질문을 분석하여 시나리오 결정"""
        
        # LLM classifier 사용 가능하면 먼저 시도
        if self.llm_classifier:
            try:
                result = self.llm_classifier.classify(user_query)
                if result.get("confidence", 0) > 0.5:
                    return result
            except Exception:
                pass
        
        # 규칙 기반 분류
        return self._rule_based_classify(user_query)
    
    def _rule_based_classify(self, user_query: str) -> Dict[str, Any]:
        """규칙 기반 시나리오 분류"""
        query_lower = user_query.lower()
        
        # 경로 추출
        local_code_path = self._extract_path(user_query)
        
        # 키워드 기반 시나리오 결정
        has_research_log = any(kw in query_lower for kw in ["연구일지", "연구 일지", "내 연구", "연구 분석"])
        has_paper_search = any(kw in query_lower for kw in ["논문", "paper", "찾아", "검색", "최신", "관련"])
        has_code_analysis = any(kw in query_lower for kw in ["코드", "code", "분석", "비교"]) or local_code_path
        has_github = "github.com" in query_lower or "github" in query_lower
        
        # 시나리오 결정
        if has_research_log:
            if has_paper_search:
                scenario = "SA-then-R"
                reasoning = "연구 일지 분석 후 관련 논문 검색"
                agents = ["SA-Agent", "R-Agent"]
            else:
                scenario = "SA-only"
                reasoning = "연구 일지 분석"
                agents = ["SA-Agent"]
        
        elif has_paper_search and has_code_analysis:
            scenario = "R-then-CA"
            reasoning = "논문 검색 후 코드 분석/비교"
            agents = ["R-Agent", "CA-Agent"]
        
        elif has_code_analysis or has_github:
            scenario = "CA-only"
            reasoning = "코드 분석"
            agents = ["CA-Agent"]
        
        elif has_paper_search:
            scenario = "R-only"
            reasoning = "논문/레퍼런스 검색"
            agents = ["R-Agent"]
        
        else:
            # 기본값: 논문 검색
            scenario = "R-only"
            reasoning = "기본 시나리오 - 논문 검색"
            agents = ["R-Agent"]
        
        return {
            "scenario": scenario,
            "agents": agents,
            "reasoning": reasoning,
            "confidence": 0.75,
            "extracted_info": {
                "local_code_path": local_code_path,
                "user_query": user_query
            }
        }
    
    def _extract_path(self, text: str) -> Optional[str]:
        """텍스트에서 파일 경로 추출"""
        import re
        
        # Linux/macOS 경로
        match = re.search(r"(/[\w\-/\.]+)", text)
        if match:
            path = match.group(1)
            if len(path) > 3:  # 짧은 경로 무시
                return path
        
        # Windows 경로
        match = re.search(r"([A-Za-z]:\\[^\s]+)", text)
        if match:
            return match.group(1)
        
        return None


class AutoAgent:
    """자동 시나리오 판별 및 실행 Agent (Task ID 기반)"""
    
    def __init__(self, use_llm: bool = False, write_to_notion: bool = True):
        """
        Args:
            use_llm: LLM 기반 분류 사용 여부
            write_to_notion: Notion에 결과 기록 여부
        """
        # API 키 로드 (shared.config 사용)
        self.config = get_config()
        api_key = self.config.openrouter_api_key
        api_url = self.config.openrouter_url
        
        # LLM 분류기 초기화 (API 키가 있으면 자동으로 LLM 사용)
        self.classifier = AutoIntentClassifier(
            use_llm=use_llm or bool(api_key),  # API 키가 있으면 LLM 사용
            api_key=api_key,
            api_url=api_url
        )
        self.executor = AgentExecutor()
        self.notion_writer = NotionWriter() if write_to_notion else None
        
        print("=" * 60)
        print("🤖 PRAA Auto Agent 초기화 완료")
        if self.notion_writer and self.notion_writer.enabled:
            print("📝 Notion 연동: 활성화")
        else:
            print("📝 Notion 연동: 비활성화")
        print("=" * 60)
    
    def run(
        self,
        user_query: str,
        local_code_path: str = None,
        research_log_path: str = None
    ) -> Dict[str, Any]:
        """
        자연어 질문을 분석하여 자동으로 적절한 Agent 실행
        
        Args:
            user_query: 사용자 질문
            local_code_path: 로컬 코드 경로 (CA-Agent용)
            research_log_path: 연구일지 경로 (SA-Agent용)
            
        Returns:
            실행 결과
        """
        # Task ID 생성
        task_id = generate_task_id()
        print(f"\n🔖 Task ID: {task_id}")
        
        # 1. 의도 분류
        print(f"\n📝 질문: {user_query}")
        print("-" * 50)
        
        intent = self.classifier.classify(user_query)
        scenario = intent["scenario"]
        agents = intent["agents"]
        reasoning = intent["reasoning"]
        confidence = intent["confidence"]
        
        print(f"🎯 시나리오: {scenario}")
        print(f"🤖 Agent: {', '.join(agents)}")
        print(f"💡 이유: {reasoning}")
        print(f"📊 신뢰도: {confidence:.0%}")
        print("-" * 50)
        
        # 외부에서 전달된 경로가 있으면 사용
        extracted_path = intent.get("extracted_info", {}).get("local_code_path")
        code_path = local_code_path or extracted_path
        
        # LLM이 추출한 검색 키워드 (R-Agent 사용 시)
        search_keywords = intent.get("search_keywords", [])
        if search_keywords:
            print(f"🔑 검색 키워드: {search_keywords}")
        
        # 2. 시나리오별 파라미터 구성 및 실행
        if scenario == "R-only":
            result = self.executor.execute({
                "scenario": "R-only",
                "params": {"R": {
                    "research_question": user_query,
                    "search_keywords": search_keywords
                }}
            })
        
        elif scenario == "SA-only":
            result = self.executor.execute({
                "scenario": "SA-only",
                "params": {"SA": {
                    "user_query": user_query,
                    "research_log_path": research_log_path
                }}
            })
        
        elif scenario == "CA-only":
            result = self.executor.execute_ca_only(
                user_query=user_query,
                local_code_path=code_path
            )
        
        elif scenario == "R-then-CA":
            result = self.executor.execute({
                "scenario": "R-then-CA",
                "params": {
                    "R": {
                        "research_question": user_query,
                        "search_keywords": search_keywords
                    },
                    "CA": {
                        "user_query": user_query,
                        "local_code_path": code_path
                    }
                }
            })
        
        elif scenario == "SA-then-R":
            result = self.executor.execute({
                "scenario": "SA-then-R",
                "params": {
                    "SA": {
                        "user_query": user_query,
                        "research_log_path": research_log_path
                    },
                    "R": {
                        "research_question": user_query,
                        "search_keywords": search_keywords
                    }
                }
            })
        
        elif scenario == "full-pipeline":
            result = self.executor.execute({
                "scenario": "full-pipeline",
                "params": {
                    "SA": {
                        "user_query": user_query,
                        "research_log_path": research_log_path
                    },
                    "R": {"search_keywords": search_keywords},
                    "CA": {
                        "user_query": user_query,
                        "local_code_path": code_path
                    }
                }
            })
        
        else:
            result = {"error": f"알 수 없는 시나리오: {scenario}"}
        
        # 3. 결과 출력
        self._print_result(scenario, result)
        
        # 4. Notion에 결과 기록
        if self.notion_writer and self.notion_writer.enabled:
            print("\n📝 Notion에 결과 기록 중...")
            
            # 각 Agent 결과 기록
            for agent_name, agent_result in result.items():
                if agent_name != "error" and isinstance(agent_result, dict):
                    content = self._format_agent_result_for_notion(agent_name, agent_result)
                    self.notion_writer.write_result(
                        task_id=task_id,
                        agent_type=agent_name.replace("_result", "").upper(),
                        title=f"{agent_name}: {user_query[:30]}...",
                        content=content,
                        metadata={"user_query": user_query}
                    )
            
            # 최종 집계 결과 기록
            notion_result = self.notion_writer.write_aggregated_result(
                task_id=task_id,
                user_query=user_query,
                results=result
            )
            
            if notion_result.get("status") == "success":
                print(f"✅ Notion 기록 완료!")
                print(f"   📄 Page URL: {notion_result.get('page_url', 'N/A')}")
        
        return {
            "task_id": task_id,
            "intent": intent,
            "result": result
        }
    
    def _format_agent_result_for_notion(
        self,
        agent_name: str,
        result: Dict[str, Any]
    ) -> str:
        """Agent 결과를 Notion 기록용 텍스트로 포맷팅"""
        lines = []
        
        status = result.get("status", "unknown")
        lines.append(f"**상태:** {status}\n")
        
        # R-Agent 논문 결과
        if result.get("results"):
            papers = result["results"]
            lines.append(f"\n**발견 논문:** {len(papers)}편\n")
            for i, paper in enumerate(papers[:5], 1):
                title = paper.get("title", "N/A")
                year = paper.get("year", "N/A")
                code = paper.get("code", [])
                github = code[0].get("repo_url") if code else "N/A"
                lines.append(f"\n### [{i}] {title} ({year})\n")
                if github != "N/A":
                    lines.append(f"- GitHub: {github}\n")
        
        # 답변
        if result.get("answer"):
            lines.append(f"\n**분석 결과:**\n\n{result['answer']}")
        
        return "".join(lines)
    
    def _print_result(self, scenario: str, result: Dict[str, Any]):
        """결과를 보기 좋게 출력"""
        print("\n" + "=" * 60)
        print(f"📊 실행 결과 ({scenario})")
        print("=" * 60)
        
        for agent_name, agent_result in result.items():
            if agent_name == "error":
                print(f"\n❌ 에러: {agent_result}")
                continue
            
            print(f"\n🤖 {agent_name} 결과:")
            print("-" * 40)
            
            if isinstance(agent_result, dict):
                status = agent_result.get("status", "unknown")
                
                if status == "success":
                    print("  ✅ 상태: 성공")
                elif status == "failed":
                    print(f"  ❌ 상태: 실패 - {agent_result.get('error', 'Unknown')}")
                else:
                    print(f"  ⚠️ 상태: {status}")
                
                # R-Agent 결과
                if agent_result.get("results"):
                    papers = agent_result["results"]
                    print(f"  📄 발견 논문: {len(papers)}편")
                    
                    for i, paper in enumerate(papers[:3], 1):
                        print(f"\n  [{i}] {paper.get('title', 'N/A')}")
                        print(f"      년도: {paper.get('year', 'N/A')}")
                        if paper.get("code"):
                            print(f"      GitHub: {paper['code'][0].get('repo_url', 'N/A')}")
                
                # CA/SA-Agent 결과
                if agent_result.get("answer"):
                    answer = agent_result["answer"]
                    if len(answer) > 500:
                        print(f"  📝 답변: {answer[:500]}...")
                    else:
                        print(f"  📝 답변: {answer}")
            else:
                print(f"  {str(agent_result)[:500]}")


def interactive_mode(agent: AutoAgent):
    """대화형 모드"""
    print("\n" + "=" * 60)
    print("🤖 PRAA Auto Agent 대화형 모드")
    print("=" * 60)
    print("\n자연어로 질문하세요. 자동으로 적절한 Agent를 선택합니다.")
    print("종료하려면 'q' 또는 'quit'를 입력하세요.\n")
    
    while True:
        try:
            query = input("\n💬 질문: ").strip()
            
            if query.lower() in ['q', 'quit', 'exit', '종료']:
                print("\n👋 안녕히 가세요!")
                break
            
            if not query:
                print("질문을 입력해주세요.")
                continue
            
            agent.run(query)
            
        except KeyboardInterrupt:
            print("\n\n👋 안녕히 가세요!")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="PRAA Auto Agent - 자연어 질문 자동 분류 및 실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python auto_agent.py "scRNAseq foundation model 논문 찾아줘"
    python auto_agent.py "내 연구일지 분석해줘"
    python auto_agent.py "DETR 논문 찾아서 코드 분석해줘"
    python auto_agent.py --local-path /path/to/code "내 코드 분석해줘"
    python auto_agent.py --no-notion "논문만 검색해줘"  # Notion 기록 없이
    python auto_agent.py  # 대화형 모드
        """
    )
    parser.add_argument("query", nargs="?", help="실행할 질문 (없으면 대화형 모드)")
    parser.add_argument("--local-path", help="분석할 로컬 코드 경로 (CA-Agent용)")
    parser.add_argument("--research-log-path", help="연구일지 경로 (SA-Agent용)")
    parser.add_argument("--use-llm", action="store_true", help="LLM 기반 분류 사용")
    parser.add_argument("--no-notion", action="store_true", help="Notion 기록 비활성화")
    
    args = parser.parse_args()
    
    # Auto Agent 초기화
    agent = AutoAgent(
        use_llm=args.use_llm,
        write_to_notion=not args.no_notion
    )
    
    if args.query:
        # 단일 질문 실행
        agent.run(
            args.query,
            local_code_path=args.local_path,
            research_log_path=args.research_log_path
        )
    else:
        # 대화형 모드
        interactive_mode(agent)


if __name__ == "__main__":
    main()
