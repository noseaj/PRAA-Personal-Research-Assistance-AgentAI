# 🤖 PRAA - Personal Research Assistance Agent

> AI 기반 연구 보조 에이전트 시스템  
> 논문 검색, 코드 분석, 연구 일지 관리를 자동화하는 멀티 에이전트 플랫폼

---

## 📋 목차

- [개요](#-개요)
- [아키텍처](#-아키텍처)
- [설치](#-설치)
- [API Key 설정](#-api-key-설정)
- [사용법](#-사용법)
- [시나리오별 예시](#-시나리오별-예시)

---

## 📖 개요

PRAA는 연구자의 일상적인 작업을 자동화하는 AI 에이전트 시스템입니다.

### 주요 기능

| 기능 | 설명 |
|------|------|
| 📄 논문 검색 | Semantic Scholar API를 통한 논문 검색 및 GitHub 레포지토리 추출 |
| 💻 코드 분석 | 논문 코드와 사용자 코드 비교 분석 |
| 📝 연구일지 분석 | 연구 진행 상황 분석 및 인사이트 제공 |
| 📊 Notion 연동 | 모든 결과를 Notion에 자동 기록 |

---

## 🏗 아키텍처

```
PRAA/
├── O-Agent/          # 🎯 오케스트레이터 (진입점)
├── R-Agent/          # 📄 논문 검색 Agent
├── CA-Agent/         # 💻 코드 분석 Agent
├── SA-Agent/         # 📝 연구일지 분석 Agent
└── shared/           # 🔧 공통 모듈
```

### Agent 설명

#### O-Agent (Orchestrator)
- **역할**: 사용자 질문을 분석하여 적절한 Agent로 라우팅
- **기능**: 의도 분류, 시나리오 결정, 결과 통합
- **진입점**: `O-Agent/auto_agent.py`

#### R-Agent (Research)
- **역할**: 논문 검색 및 관련 GitHub 레포지토리 추출
- **기능**: Semantic Scholar 검색, 논문 메타데이터 추출, GitHub URL 파싱

#### CA-Agent (Code Analysis)
- **역할**: 코드 분석 및 비교
- **기능**: 레퍼런스 코드 분석, 사용자 코드 분석, 통합 비교

#### SA-Agent (Study Analysis)
- **역할**: 연구 일지 분석
- **기능**: 연구 진행 상황 요약, 인사이트 제공

---

## 🔧 설치

### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/PRAA.git
cd PRAA
```

### 2. 가상환경 생성 및 활성화

```bash
# Conda
conda create -n praa python=3.10
conda activate praa

# 또는 venv
python -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

---

## 🔑 API Key 설정

### 1. apikey.json 생성

프로젝트 루트에 `apikey.json` 파일을 생성합니다:

```bash
cp apikey_template.json apikey.json
```

### 2. apikey.json 편집

```json
{
    "OpenRouterAPIKey": "sk-or-v1-xxxxx",
    "OpenRouterURL": "https://openrouter.ai/api/v1",
    "NotionAPIKey": "secret_xxxxx",
    "NotionPageID": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "SemanticScholarAPIKey": "xxxxx",
    "GitHubToken": "ghp_xxxxx"
}
```

### 필수 API Key

| Key | 용도 | 발급 링크 |
|-----|------|-----------|
| `OpenRouterAPIKey` | LLM 호출 (Claude, GPT 등) | [openrouter.ai](https://openrouter.ai) |
| `NotionAPIKey` | Notion 연동 | [Notion Integration](https://www.notion.so/my-integrations) |
| `NotionPageID` | 결과 저장 페이지 | Notion 페이지 URL에서 추출 |

### 선택 API Key

| Key | 용도 | 발급 링크 |
|-----|------|-----------|
| `SemanticScholarAPIKey` | 논문 검색 (선택) | [Semantic Scholar](https://www.semanticscholar.org/product/api) |
| `GitHubToken` | Private repo 접근 | [GitHub Settings](https://github.com/settings/tokens) |

> ⚠️ **주의**: `apikey.json`은 `.gitignore`에 포함되어 git에 업로드되지 않습니다.

---

## 🚀 사용법

### 기본 명령어

```bash
# 프로젝트 루트에서 실행
cd PRAA

# 대화형 모드
python main.py

# 단일 질문 실행
python main.py "질문 내용"

# 옵션 확인
python main.py --help
```

### 주요 옵션

| 옵션 | 설명 |
|------|------|
| `--local-path /path` | CA-Agent에서 분석할 로컬 코드 경로 |
| `--research-log-path /path` | SA-Agent에서 분석할 연구일지 경로 |
| `--no-notion` | Notion 기록 비활성화 |
| `--use-llm` | LLM 기반 의도 분류 사용 (기본: 규칙 기반) |

---

## 📚 시나리오별 예시

### 1. R-only: 논문 검색

> "DETR 논문에 대해 찾아줘"

```bash
python main.py "DETR object detection 논문 찾아줘"
```

**결과:**
- Semantic Scholar에서 관련 논문 검색
- 각 논문의 GitHub 레포지토리 URL 추출
- Notion에 논문 목록 기록

---

### 2. CA-only: 코드 분석

> "내 코드를 분석해줘"

```bash
python main.py --local-path /path/to/mycode "내 코드 분석해줘"
```

**결과:**
- 로컬 코드 구조 분석
- 주요 함수/클래스 파악
- 개선점 제안

---

### 3. SA-only: 연구일지 분석

> "내 연구 일지를 분석해줘"

```bash
python main.py --research-log-path ./my_notes "내 연구일지 분석해줘"
```

**결과:**
- 연구 진행 상황 요약
- 주요 인사이트 추출
- 다음 단계 제안

---

### 4. R-then-CA: 논문 검색 → 코드 분석

> "DETR 논문 찾아서 코드 분석해줘"

```bash
python main.py "DETR 논문 찾아서 GitHub 코드 분석해줘"
```

**결과:**
1. **R-Agent**: DETR 관련 논문 검색 및 GitHub URL 추출
2. **CA-Agent**: GitHub 코드 클론 및 분석
3. Notion에 논문 정보 + 코드 분석 결과 기록

---

### 5. SA-then-R: 연구일지 → 논문 검색

> "내 연구와 관련된 논문 찾아줘"

```bash
python main.py --research-log-path ./notes "내 연구와 관련된 논문 찾아줘"
```

**결과:**
1. **SA-Agent**: 연구일지 분석하여 핵심 키워드 추출
2. **R-Agent**: 추출된 키워드로 관련 논문 검색
3. Notion에 연구 분석 + 추천 논문 기록

---

## 📁 프로젝트 구조

```
PRAA/
│
├── main.py                    # ⭐ 메인 진입점
│
├── O-Agent/                    # 오케스트레이터
│   ├── auto_agent.py          # Auto Agent 구현
│   ├── config.py              # 설정 (shared 래핑)
│   ├── agents/                # Agent wrappers
│   │   ├── r_agent_wrapper.py
│   │   ├── ca_agent_wrapper.py
│   │   └── sa_agent_wrapper.py
│   └── orchestrator/          # 의도 분류 및 실행
│       ├── intent_classifier.py
│       └── agent_executor.py
│
├── R-Agent/                    # 논문 검색
│   ├── run_agent.py
│   ├── config.py
│   └── agents/research_agent.py
│
├── CA-Agent/                   # 코드 분석
│   ├── CA_main.py
│   ├── config/llm_config.py
│   ├── agents/                # 분석 에이전트들
│   │   ├── reference_agent.py
│   │   ├── mycode_agent.py
│   │   ├── integration_agent.py
│   │   └── answer_agent.py
│   └── repo/                  # GitHub 클론/파싱
│
├── SA-Agent/                   # 연구일지 분석
│   ├── SA_main.py
│   ├── config/llm_config.py
│   └── agent/study_agent.py
│
├── shared/                     # 공통 모듈
│   ├── config.py              # 통합 설정
│   ├── llm_client.py          # LLM 클라이언트
│   └── notion/                # Notion 연동
│
├── apikey.json                # API 키 (gitignore)
├── apikey_template.json       # API 키 템플릿
└── requirements.txt           # 의존성
```


