# 🎯 O-Agent (Orchestrator Agent)

> 사용자 질문을 분석하고 적절한 Agent로 라우팅하는 오케스트레이터

---

## 📋 개요

O-Agent는 PRAA 시스템의 **진입점**으로, 다음 역할을 수행합니다:

1. **의도 분류 (Intent Classification)**: 사용자 질문 분석
2. **시나리오 결정**: 어떤 Agent를 어떤 순서로 호출할지 결정
3. **Agent 실행**: R-Agent, CA-Agent, SA-Agent 호출
4. **결과 통합**: 여러 Agent 결과를 하나로 집계
5. **Notion 기록**: 최종 결과를 Notion에 저장

---

## 📥 입력 (Input)

### 사용자 질문 (자연어)

```python
user_query = "DETR 논문 찾아서 코드 분석해줘"
```

### 옵션 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `user_query` | str | 사용자 질문 (필수) |
| `local_code_path` | str | 로컬 코드 경로 (CA-Agent용) |
| `research_log_path` | str | 연구일지 경로 (SA-Agent용) |

---

## 📤 출력 (Output)

### 반환 형식

```python
{
    "task_id": "PRAA-20260116-123456",
    "intent": {
        "scenario": "R-then-CA",
        "agents": ["R-Agent", "CA-Agent"],
        "reasoning": "논문 검색 후 코드 분석",
        "confidence": 0.95,
        "search_keywords": ["DETR", "object detection"]
    },
    "result": {
        "r_result": { ... },   # R-Agent 결과
        "ca_result": { ... }   # CA-Agent 결과
    }
}
```

---

## 🔄 시나리오별 데이터 흐름

### 1. R-only (논문 검색만)

```
User Query
    ↓
┌─────────────┐
│  O-Agent    │ → Intent: "R-only"
└─────────────┘
    ↓
┌─────────────┐
│  R-Agent    │ ← params: {research_question, search_keywords}
└─────────────┘
    ↓
    Output: {papers: [...], github_urls: [...]}
    ↓
┌─────────────┐
│   Notion    │ ← 결과 기록
└─────────────┘
```

### 2. SA-only (연구일지 분석만)

```
User Query + research_log_path
    ↓
┌─────────────┐
│  O-Agent    │ → Intent: "SA-only"
└─────────────┘
    ↓
┌─────────────┐
│  SA-Agent   │ ← params: {user_query, research_log_path}
└─────────────┘
    ↓
    Output: {analysis, insights}
```

### 3. CA-only (코드 분석만)

```
User Query + local_code_path
    ↓
┌─────────────┐
│  O-Agent    │ → Intent: "CA-only"
└─────────────┘
    ↓
┌─────────────┐
│  CA-Agent   │ ← params: {user_query, local_code_path}
└─────────────┘
    ↓
    Output: {answer, analysis}
```

### 4. R-then-CA (논문 검색 → 코드 분석)

```
User Query: "DETR 논문 찾아서 코드 분석해줘"
    ↓
┌─────────────┐
│  O-Agent    │ → Intent: "R-then-CA"
└─────────────┘
    ↓
┌─────────────┐
│  R-Agent    │ ← params: {research_question, search_keywords: ["DETR"]}
└─────────────┘
    ↓
    Output: {papers: [{github: "https://github.com/xxx"}]}
    ↓
    ★ O-Agent가 GitHub URL 추출
    ↓
┌─────────────┐
│  CA-Agent   │ ← params: {reference_github: "https://github.com/xxx"}
└─────────────┘
    ↓
    Output: {answer, code_analysis}
    ↓
┌─────────────┐
│   Notion    │ ← 통합 결과 기록
└─────────────┘
```

### 5. SA-then-R (연구일지 → 논문 검색)

```
User Query + research_log_path
    ↓
┌─────────────┐
│  O-Agent    │ → Intent: "SA-then-R"
└─────────────┘
    ↓
┌─────────────┐
│  SA-Agent   │ ← params: {user_query, research_log_path}
└─────────────┘
    ↓
    Output: {keywords: ["scRNA-seq", "foundation model"]}
    ↓
    ★ O-Agent가 키워드 추출
    ↓
┌─────────────┐
│  R-Agent    │ ← params: {search_keywords: ["scRNA-seq", "foundation model"]}
└─────────────┘
    ↓
    Output: {papers: [...]}
    ↓
┌─────────────┐
│   Notion    │ ← 통합 결과 기록
└─────────────┘
```

---

## 📁 파일 구조

```
O-Agent/
├── auto_agent.py          # 메인 진입점
├── config.py              # 설정 (shared 래핑)
├── agents/                # Agent Wrappers
│   ├── r_agent_wrapper.py
│   ├── ca_agent_wrapper.py
│   └── sa_agent_wrapper.py
└── orchestrator/
    ├── intent_classifier.py   # 의도 분류기
    └── agent_executor.py      # Agent 실행기
```

---

## 🔧 사용법

```bash
# 프로젝트 루트에서
python main.py "논문 찾아줘"

# 또는 O-Agent 디렉토리에서
cd O-Agent
python auto_agent.py "논문 찾아줘"
```

---

## 📊 Notion 연동

O-Agent는 모든 결과를 Notion에 자동 기록합니다:

1. **Task ID 기반**: 각 실행에 고유 ID 부여
2. **Agent별 결과**: 각 Agent 결과 개별 기록
3. **통합 보고서**: LLM으로 요약한 최종 보고서
