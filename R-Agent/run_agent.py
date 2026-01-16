#!/usr/bin/env python3
"""
R-Agent를 CLI로 실행하고 결과를 JSON으로 출력
"""
import sys
import json
from agents.research_agent import RAgent, AgentConfig


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python run_agent.py <question>"}))
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    
    try:
        cfg = AgentConfig(output_dir="./output")
        agent = RAgent(cfg)
        result = agent.run(question)
        
        # JSON으로 출력
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
