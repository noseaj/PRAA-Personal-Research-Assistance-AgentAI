# 📝 SA-Agent (Study Analysis Agent)

> 연구일지 분석 및 인사이트 추출 Agent

---

## 📋 개요

SA-Agent는 **연구일지 분석**을 담당하는 Agent입니다:

1. **텍스트 로딩**: 연구일지/노트 파일 읽기
2. **내용 분석**: LLM 기반 내용 이해 및 분석
3. **키워드 추출**: 연구 관련 핵심 키워드 추출 (R-Agent 연동용)
4. **인사이트 생성**: 연구 진행 상황 요약 및 제안

---

## 📥 입력 (Input)

### O-Agent로부터 받는 파라미터

```python
{
    "user_query": "내 연구일지 분석해줘",
    "research_log_path": "/home/user/research_notes/"
}
```

### 파라미터 설명

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `user_query` | str | ✅ | 사용자 질문 |
| `research_log_path` | str | ✅ | 연구일지 파일/폴더 경로 |

### 지원 파일 형식

- `.txt` - 텍스트 파일
- `.md` - 마크다운 파일
- `.pkl` - 임베딩 파일 (사전 처리된 연구 노트)

---

## 📤 출력 (Output)

### O-Agent에게 반환하는 형식

```python
{
    "status": "success",
    "answer": "## 연구일지 분석 결과\n\n...",
    "keywords": ["scRNA-seq", "foundation model", "cell type annotation"],
    "insights": [
        "최근 연구는 scRNA-seq 데이터 분석에 집중",
        "foundation model 접근법 시도 중",
        "다음 단계: 벤치마크 데이터셋 확보 필요"
    ],
    "summary": "연구 진행 상황 요약..."
}
```

### 결과 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | str | "success" 또는 "failed" |
| `answer` | str | LLM 기반 분석 답변 |
| `keywords` | list[str] | **추출된 연구 키워드** (R-Agent 연동용) |
| `insights` | list[str] | 주요 인사이트 목록 |
| `summary` | str | 연구 진행 상황 요약 |

---

## 🔄 O-Agent와의 연동

### 1. SA-only 시나리오

```
O-Agent
    │
    │  params = {
    │      "user_query": "내 연구일지 분석해줘",
    │      "research_log_path": "/home/user/notes/"
    │  }
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   SA-Agent                       │
│                                                  │
│  1. research_log_path에서 파일 로드              │
│  2. 텍스트 내용 분석                             │
│  3. 인사이트 및 요약 생성                        │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  return {
    │      "answer": "연구 분석 결과...",
    │      "keywords": ["scRNA-seq", "..."],
    │      "insights": [...]
    │  }
    │
    ▼
O-Agent → Notion 기록
```

### 2. SA-then-R 시나리오 (가장 중요!)

```
User Query: "내 연구와 관련된 논문 찾아줘"
    │
    ▼
O-Agent → Intent: "SA-then-R"
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   SA-Agent                       │
│                                                  │
│  Input: {                                        │
│      "user_query": "내 연구와 관련된 논문 찾아줘", │
│      "research_log_path": "/home/user/notes/"    │
│  }                                               │
│                                                  │
│  ★ 연구일지 분석 후 키워드 추출                   │
│                                                  │
│  Output: {                                       │
│      "keywords": [                               │
│          "scRNA-seq",                            │
│          "foundation model",                     │
│          "cell type annotation"                  │
│      ]                                           │
│  }                                               │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  ★ O-Agent가 keywords 추출
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   R-Agent                        │
│                                                  │
│  Input: {                                        │
│      "search_keywords": [                        │
│          "scRNA-seq",             ★ SA에서 전달  │
│          "foundation model",                     │
│          "cell type annotation"                  │
│      ]                                           │
│  }                                               │
│                                                  │
│  ★ 연구 키워드 기반으로 관련 논문 검색            │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  Output: {results: [...related papers...]}
    │
    ▼
O-Agent → Notion 기록 (연구분석 + 추천논문)
```

### 3. 데이터 흐름 상세

```
                    SA-Agent
                       │
                       │ keywords: ["scRNA-seq", "foundation model"]
                       │
                       ▼
        ┌──────────────────────────────┐
        │          O-Agent             │
        │                              │
        │  search_keywords = sa_result │
        │      .get("keywords", [])    │
        │                              │
        └──────────────────────────────┘
                       │
                       │ search_keywords: ["scRNA-seq", "foundation model"]
                       │
                       ▼
                    R-Agent
                       │
                       │ Semantic Scholar 검색
                       │
                       ▼
               관련 논문 반환
```

---

## 📁 파일 구조

```
SA-Agent/
├── SA_main.py               # 메인 진입점
├── config/
│   └── llm_config.py        # LLM 설정 (shared 래핑)
└── agent/
    └── study_agent.py       # 연구일지 분석 로직
```

---

## 🔧 직접 실행

```bash
cd SA-Agent
python SA_main.py --path /home/user/research_notes/
```

또는 CLI:

```bash
python main.py --research-log-path ./notes "내 연구일지 분석해줘"
```

---

## ⚙️ 키워드 추출 로직

SA-Agent의 핵심 기능 중 하나는 **연구 키워드 추출**입니다.  
추출된 키워드는 R-Agent의 논문 검색에 사용됩니다.

### 키워드 추출 방식

```python
# LLM 프롬프트 예시
"""
아래 연구일지를 분석하여 관련 논문 검색에 사용할 수 있는 
핵심 키워드를 추출해주세요.

연구일지:
{research_log_content}

요구사항:
1. 영어 학술 키워드 3-5개
2. 기술/방법론 중심
3. Semantic Scholar에서 검색 가능한 용어

예시 출력:
["scRNA-seq", "cell type annotation", "foundation model", "transformer"]

키워드:
"""
```

### 키워드 활용

| 단계 | Agent | 키워드 사용 |
|------|-------|------------|
| 1 | SA-Agent | 연구일지에서 키워드 추출 |
| 2 | O-Agent | SA 결과에서 keywords 필드 추출 |
| 3 | R-Agent | search_keywords로 논문 검색 |

---

## 📊 분석 결과 예시

### 입력 (연구일지)

```markdown
# 2026-01-15 연구 노트

## 진행 상황
- scRNA-seq 데이터 전처리 완료
- Foundation model (scGPT) 테스트 중
- Cell type annotation 정확도 개선 필요

## 다음 계획
- 다른 foundation model 비교 (scBERT, Geneformer)
- 벤치마크 데이터셋 확보
```

### 출력

```python
{
    "status": "success",
    "answer": "## 연구 분석 결과\n\n현재 scRNA-seq 데이터 분석...",
    "keywords": ["scRNA-seq", "foundation model", "cell type annotation", "scGPT"],
    "insights": [
        "scRNA-seq 데이터 전처리 완료, 모델 테스트 단계",
        "Foundation model 접근법 (scGPT) 시도 중",
        "다른 모델(scBERT, Geneformer) 비교 검토 필요"
    ],
    "summary": "scRNA-seq 기반 cell type annotation 연구 진행 중. Foundation model 활용 단계."
}
```

---

## ⚠️ 주의사항

1. **영어 키워드**: `keywords`는 항상 **영어**로 추출 (R-Agent 호환)
2. **파일 인코딩**: UTF-8 인코딩 권장
3. **파일 크기**: 대용량 파일은 샘플링하여 분석
