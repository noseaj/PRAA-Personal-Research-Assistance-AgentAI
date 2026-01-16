# 💻 CA-Agent (Code Analysis Agent)

> 코드 분석 및 논문 코드 비교 Agent

---

## 📋 개요

CA-Agent는 **코드 분석**을 담당하는 Agent입니다:

1. **레퍼런스 코드 분석**: GitHub 레포지토리 클론 및 분석
2. **사용자 코드 분석**: 로컬 코드 구조 파악
3. **비교 분석**: 레퍼런스와 사용자 코드 비교
4. **답변 생성**: LLM 기반 분석 결과 생성

---

## 📥 입력 (Input)

### O-Agent로부터 받는 파라미터

```python
{
    "user_query": "DETR 코드와 내 코드 비교해줘",
    "local_code_path": "/home/user/my_project",      # 선택
    "reference_github": "https://github.com/facebookresearch/detr",  # R-Agent에서 전달
    "reference_paper_text": "DETR: End-to-End...",   # 선택
    "reference_paper_title": "DETR"                  # 선택
}
```

### 파라미터 설명

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `user_query` | str | ✅ | 사용자 질문 |
| `local_code_path` | str | ❌ | 분석할 로컬 코드 경로 |
| `reference_github` | str | ❌ | 레퍼런스 GitHub URL (R-Agent에서 전달) |
| `reference_paper_text` | str | ❌ | 논문 텍스트 |
| `reference_paper_title` | str | ❌ | 논문 제목 |

---

## 📤 출력 (Output)

### O-Agent에게 반환하는 형식

```python
{
    "status": "success",
    "answer": "## 코드 분석 결과\n\n...",
    "paper_name": "DETR",
    "local_code_path": "/home/user/my_project",
    "json_path": "CA-outputs/analysis_20260116.json",
    "has_mycode_analysis": True,
    "has_reference_analysis": True,
    "has_integration": True
}
```

### 결과 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | str | "success" 또는 "failed" |
| `answer` | str | **LLM 기반 분석 답변** (마크다운) |
| `has_mycode_analysis` | bool | 로컬 코드 분석 수행 여부 |
| `has_reference_analysis` | bool | 레퍼런스 분석 수행 여부 |
| `has_integration` | bool | 통합 비교 분석 수행 여부 |

---

## 🔄 O-Agent와의 연동

### 1. CA-only 시나리오 (로컬 코드만 분석)

```
O-Agent
    │
    │  params = {
    │      "user_query": "코드 분석해줘",
    │      "local_code_path": "/home/user/my_project"
    │  }
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   CA-Agent                       │
│                                                  │
│  1. local_code_path에서 코드 파싱                 │
│  2. MyCodeAgent로 구조 분석                      │
│  3. AnswerAgent로 답변 생성                      │
│                                                  │
│  ★ reference_github가 없으므로                   │
│    ReferenceAgent, IntegrationAgent 스킵         │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  return {
    │      "answer": "...",
    │      "has_mycode_analysis": True,
    │      "has_reference_analysis": False,
    │      "has_integration": False
    │  }
    │
    ▼
O-Agent → Notion 기록
```

### 2. R-then-CA 시나리오 (가장 중요!)

```
R-Agent
    │
    │  Output: {
    │      results: [{
    │          code: [{repo_url: "github.com/facebookresearch/detr"}]
    │      }]
    │  }
    │
    ▼
O-Agent (GitHub URL 추출)
    │
    │  ★ 첫 번째 논문의 첫 번째 GitHub URL 선택
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   CA-Agent                       │
│                                                  │
│  Input: {                                        │
│      "user_query": "코드 분석해줘",               │
│      "reference_github": "github.com/.../detr",  │
│      "local_code_path": "/home/.../my_code"      │
│  }                                               │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│            CA-Agent 내부 파이프라인               │
│                                                  │
│  1. clone_repo(reference_github)                │
│     └→ /tmp/repos/detr/                         │
│                                                  │
│  2. ReferenceAgent.run(ref_code)                │
│     └→ reference_analysis                       │
│                                                  │
│  3. MyCodeAgent.run(my_code)                    │
│     └→ mycode_analysis                          │
│                                                  │
│  4. IntegrationAgent.run(ref, my)               │
│     └→ integration_result  ★ 비교 분석          │
│                                                  │
│  5. AnswerAgent.answer(query, ref, my, int)     │
│     └→ final_answer                             │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  return {
    │      "answer": "## 비교 분석 결과\n...",
    │      "has_reference_analysis": True,
    │      "has_mycode_analysis": True,
    │      "has_integration": True
    │  }
    │
    ▼
O-Agent → Notion 기록
```

### 3. 레퍼런스만 분석 (local_code_path 없음)

```
O-Agent
    │
    │  params = {
    │      "user_query": "DETR 코드 분석해줘",
    │      "reference_github": "github.com/.../detr"
    │      # local_code_path 없음!
    │  }
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   CA-Agent                       │
│                                                  │
│  1. clone_repo(reference_github)                │
│  2. ReferenceAgent.run(ref_code)                │
│  3. AnswerAgent.answer(query, ref_analysis)     │
│                                                  │
│  ★ MyCodeAgent, IntegrationAgent 스킵           │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  return {
    │      "answer": "## DETR 코드 분석\n...",
    │      "has_reference_analysis": True,
    │      "has_mycode_analysis": False,
    │      "has_integration": False
    │  }
    │
    ▼
O-Agent
```

---

## 📁 파일 구조

```
CA-Agent/
├── CA_main.py               # 메인 파이프라인
├── config/
│   └── llm_config.py        # LLM 설정 (shared 래핑)
├── agents/
│   ├── reference_agent.py   # 레퍼런스 코드 분석
│   ├── mycode_agent.py      # 로컬 코드 분석
│   ├── integration_agent.py # 비교 분석
│   └── answer_agent.py      # 답변 생성
├── repo/
│   ├── clone.py             # GitHub 클론
│   └── parser.py            # 코드 파싱
├── notion/                  # (레거시, shared 사용 권장)
└── utils/
    └── prompt_loader.py     # 프롬프트 로딩
```

---

## 🔧 직접 실행

```bash
cd CA-Agent
python CA_main.py
```

또는 CLI:

```bash
python main.py --local-path /path/to/code "내 코드 분석해줘"
```

---

## ⚙️ 내부 Agent 설명

### 1. ReferenceAgent
- **역할**: GitHub 레퍼런스 코드 분석
- **입력**: 파싱된 함수/클래스 목록
- **출력**: 구조 분석 결과

### 2. MyCodeAgent
- **역할**: 로컬 코드 분석
- **입력**: 파싱된 함수/클래스 목록
- **출력**: 구조 분석 결과

### 3. IntegrationAgent
- **역할**: 레퍼런스 vs 로컬 비교
- **입력**: reference_analysis, mycode_analysis
- **출력**: 비교 분석 결과

### 4. AnswerAgent
- **역할**: 최종 답변 생성
- **입력**: 모든 분석 결과 + user_query
- **출력**: 마크다운 형식 답변

---

## 🔄 파싱 프로세스

```
GitHub URL / Local Path
         │
         ▼
┌─────────────────────┐
│    repo/clone.py    │  ← GitHub 클론 (필요시)
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│   repo/parser.py    │  ← Python 파일 파싱
└─────────────────────┘
         │
         ▼
    함수/클래스 목록
    [
        {"name": "forward", "code": "def forward...", "type": "function"},
        {"name": "DETR", "code": "class DETR...", "type": "class"},
        ...
    ]
```
