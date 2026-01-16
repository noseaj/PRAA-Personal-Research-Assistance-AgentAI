#!/usr/bin/env python3
"""
PRAA - Personal Research Assistance Agent
메인 진입점

사용법:
    python main.py "논문 찾아줘"                               # R-only
    python main.py "내 연구일지 분석해줘"                       # SA-only  
    python main.py "DETR 논문 찾아서 코드 분석해줘"            # R-then-CA
    python main.py --local-path /path/to/code "코드 분석"      # CA-only
    python main.py --research-log-path ./notes "연구 분석"     # SA-only
    python main.py                                             # 대화형 모드
    
옵션:
    --local-path PATH      CA-Agent에서 분석할 로컬 코드 경로
    --research-log-path    SA-Agent에서 분석할 연구일지 경로
    --no-notion            Notion 기록 비활성화
    --use-llm              LLM 기반 의도 분류 사용
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "O-Agent"))

# 작업 디렉토리를 프로젝트 루트로 변경
os.chdir(PROJECT_ROOT)

# O-Agent의 auto_agent import 및 실행
import importlib.util

def load_auto_agent():
    """O-Agent/auto_agent.py 동적 로드"""
    auto_agent_path = PROJECT_ROOT / "O-Agent" / "auto_agent.py"
    spec = importlib.util.spec_from_file_location("auto_agent", auto_agent_path)
    auto_agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auto_agent)
    return auto_agent


if __name__ == "__main__":
    auto_agent = load_auto_agent()
    auto_agent.main()
