"""
SA-Agent Wrapper - subprocess로 실행
"""
from typing import Optional
import subprocess
import sys
from pathlib import Path


class SAAgentWrapper:
    """SA-Agent 래퍼 - subprocess 실행 방식"""
    
    def __init__(self):
        """SA-Agent 초기화"""
        self.sa_agent_path = Path(__file__).parent.parent.parent / "SA-Agent"
        self.python_path = sys.executable
        print("[SA-Agent] ✅ Wrapper 초기화")
    
    def run(
        self,
        pkl_path: Optional[str] = None
    ) -> str:
        """
        SA-Agent 실행 (subprocess)
        
        Args:
            pkl_path: 연구 로그 pkl 파일 경로 (기본: embeddings.pkl)
            
        Returns:
            연구 일지 분석 결과 (문자열)
        """
        try:
            print(f"\n[SA-Agent] 실행 중: 연구 일지 분석")
            
            if pkl_path is None:
                pkl_path = str(self.sa_agent_path / "embeddings.pkl")
            
            # Python 스크립트 생성
            script = f"""
import sys
sys.path.insert(0, '{self.sa_agent_path}')
from agents.study_agent import study_agent

pkl_path = '{pkl_path}'
try:
    result = study_agent(pkl_path)
    print("===RESULT_START===")
    print(result)
    print("===RESULT_END===")
except FileNotFoundError:
    print("===RESULT_START===")
    print("[SA-Agent] 연구 로그 파일이 없습니다. 연구 로그를 먼저 작성해주세요.")
    print("===RESULT_END===")
except Exception as e:
    print("===RESULT_START===")
    print(f"[SA-Agent 에러] {{str(e)}}")
    print("===RESULT_END===")
"""
            
            # subprocess로 실행
            result = subprocess.run(
                [self.python_path, '-c', script],
                cwd=str(self.sa_agent_path),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # 결과 파싱
            output = result.stdout
            if "===RESULT_START===" in output and "===RESULT_END===" in output:
                start = output.index("===RESULT_START===") + len("===RESULT_START===")
                end = output.index("===RESULT_END===")
                answer = output[start:end].strip()
            else:
                answer = output.strip() if output.strip() else "[SA-Agent] 결과 없음"
            
            print(f"[SA-Agent] ✅ 완료")
            return answer
            
        except subprocess.TimeoutExpired:
            return "[SA-Agent 타임아웃] 120초 초과"
        except Exception as e:
            print(f"[SA-Agent] ❌ 에러: {e}")
            import traceback
            traceback.print_exc()
            return f"[SA-Agent 에러] {str(e)}"
