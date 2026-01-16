# 📄 R-Agent (Research Agent)

> 논문 검색 및 GitHub 레포지토리 추출 Agent

---

## 📋 개요

R-Agent는 **논문 검색**을 담당하는 Agent입니다:

1. **Semantic Scholar 검색**: 학술 논문 검색
2. **메타데이터 추출**: 제목, 저자, 년도, 초록
3. **GitHub URL 추출**: 논문 관련 코드 레포지토리 URL 파싱
4. **결과 반환**: O-Agent에게 구조화된 데이터 전달

---

## 📥 입력 (Input)

### O-Agent로부터 받는 파라미터

```python
{
    "research_question": "DETR object detection 논문 찾아줘",
    "search_keywords": ["DETR", "object detection", "transformer"]
}
```

### 파라미터 설명

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `research_question` | str | 원본 사용자 질문 | "DETR 논문 찾아줘" |
| `search_keywords` | list[str] | **영어** 검색 키워드 | ["DETR", "detection"] |

> ⚠️ **중요**: `search_keywords`는 반드시 **영어**로 전달되어야 합니다.  
> O-Agent의 IntentClassifier가 한글 질문을 영어 키워드로 변환합니다.

---

## 📤 출력 (Output)

### O-Agent에게 반환하는 형식

```python
{
    "status": "success",
    "query": "DETR object detection",
    "results": [
        {
            "title": "End-to-End Object Detection with Transformers",
            "authors": ["Nicolas Carion", "Francisco Massa", ...],
            "year": 2020,
            "abstract": "We present DETR...",
            "url": "https://arxiv.org/abs/2005.12872",
            "citations": 12000,
            "code": [
                {
                    "repo_url": "https://github.com/facebookresearch/detr",
                    "stars": 9500
                }
            ]
        },
        ...
    ],
    "total_found": 10
}
```

### 결과 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | str | "success" 또는 "failed" |
| `results` | list | 검색된 논문 목록 |
| `results[].title` | str | 논문 제목 |
| `results[].code` | list | GitHub 레포지토리 목록 |
| `results[].code[].repo_url` | str | **GitHub URL** (CA-Agent로 전달) |

---

## 🔄 O-Agent와의 연동

### 1. R-only 시나리오

```
O-Agent
    │
    │  params = {
    │      "research_question": "DETR 논문",
    │      "search_keywords": ["DETR", "object detection"]
    │  }
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   R-Agent                        │
│                                                  │
│  1. search_keywords로 Semantic Scholar 검색      │
│  2. 논문 메타데이터 추출                          │
│  3. GitHub URL 파싱                              │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  return {
    │      "status": "success",
    │      "results": [{title, authors, code: [{repo_url}]}]
    │  }
    │
    ▼
O-Agent → Notion 기록
```

### 2. R-then-CA 시나리오 (중요!)

```
O-Agent
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   R-Agent                        │
│                                                  │
│  Input: {search_keywords: ["DETR"]}              │
│                                                  │
│  Output: {                                       │
│      results: [{                                 │
│          title: "DETR...",                       │
│          code: [{                                │
│              repo_url: "github.com/xxx/detr"  ★  │
│          }]                                      │
│      }]                                          │
│  }                                               │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  ★ O-Agent가 repo_url 추출
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   CA-Agent                       │
│                                                  │
│  Input: {                                        │
│      reference_github: "github.com/xxx/detr" ★   │
│      user_query: "코드 분석해줘"                  │
│  }                                               │
│                                                  │
└─────────────────────────────────────────────────┘
```

### 3. SA-then-R 시나리오

```
SA-Agent
    │
    │  Output: {keywords: ["scRNA-seq", "foundation"]}
    │
    ▼
O-Agent (키워드 변환)
    │
    ▼
┌─────────────────────────────────────────────────┐
│                   R-Agent                        │
│                                                  │
│  Input: {                                        │
│      search_keywords: ["scRNA-seq", "foundation"]│
│  }                                               │
│                                                  │
│  ★ SA-Agent에서 추출된 연구 키워드로 검색         │
│                                                  │
└─────────────────────────────────────────────────┘
    │
    │  Output: {results: [...related papers...]}
    │
    ▼
O-Agent → Notion 기록
```

---

## 📁 파일 구조

```
R-Agent/
├── run_agent.py              # 실행 진입점
├── config.py                 # 설정 (shared 래핑)
└── agents/
    └── research_agent.py     # 핵심 검색 로직
```

---

## 🔧 직접 실행

```bash
cd R-Agent
python run_agent.py "DETR object detection"
```

---

## ⚙️ 설정

### API Key (apikey.json)

```json
{
    "SemanticScholarAPIKey": "xxxxx"  // 선택사항
}
```

- Semantic Scholar API Key가 없어도 동작하지만, rate limit이 있음
- API Key 발급: [Semantic Scholar API](https://www.semanticscholar.org/product/api)

---

## 🔍 검색 로직

1. **키워드 조합**: `search_keywords`를 공백으로 연결
2. **Semantic Scholar 검색**: Paper Search API 호출
3. **결과 필터링**: GitHub 코드가 있는 논문 우선
4. **정렬**: 인용수 기준 내림차순
