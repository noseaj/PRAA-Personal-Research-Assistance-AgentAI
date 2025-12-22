"""
CA-Agent Wrapper - subprocess로 실행
"""
from typing import Optional
import subprocess
import sys
from pathlib import Path


class CAAgentWrapper:
    """CA-Agent 래퍼 - subprocess 실행 방식"""
    
    def __init__(self):
        """CA-Agent 초기화"""
        self.ca_agent_path = Path(__file__).parent.parent.parent / "CA-Agent"
        self.python_path = sys.executable
        print("[CA-Agent] ✅ Wrapper 초기화")
    
    def run(
        self,
        user_query: str,
        local_code_path: Optional[str] = None,
        reference_paper: Optional[str] = None,
        reference_github: Optional[str] = None
    ) -> str:
        """
        CA-Agent 실행 (subprocess)
        
        Returns:
            코드 분석 결과 (문자열)
        """
        try:
            print(f"\n[CA-Agent] 실행 중: {user_query}")
            
            # Python 스크립트 생성
            script = f"""
import sys
sys.path.insert(0, '{self.ca_agent_path}')
from CA_main import run_pipeline
result = run_pipeline('''{user_query}''')
print("===RESULT_START===")
print(result)
print("===RESULT_END===")
"""
            
            # subprocess로 실행
            result = subprocess.run(
                [self.python_path, '-c', script],
                cwd=str(self.ca_agent_path),
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
                # 전체 출력에서 === ANSWER === 부분 찾기
                if "=== ANSWER ===" in output:
                    answer = output.split("=== ANSWER ===")[1].strip()
                else:
                    answer = output
            
            print(f"[CA-Agent] ✅ 완료")
            return answer
            
        except subprocess.TimeoutExpired:
            return "[CA-Agent 타임아웃] 120초 초과"
        except Exception as e:
            print(f"[CA-Agent] ❌ 에러: {e}")
            import traceback
            traceback.print_exc()
            return f"[CA-Agent 에러] {str(e)}"
