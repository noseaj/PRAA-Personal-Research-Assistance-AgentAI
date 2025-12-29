# Research Agent Assistant (R-Agent)

Research Agent는 주어진 연구 주제 또는 키워드를 기반으로 다음과 같은 작업을 자동으로 수행하는 리서치 파이프라인입니다.

- 논문/문서 수집 및 정제
- PDF 문서 파싱 및 텍스트 추출
- GitHub 레포지토리 구조 분석
- 내용 요약 및 구조화
- 결과를 JSON / CSV 형태로 저장

이 에이전트는 리서치 자동화와 기술 트렌드 조사를 목적으로 설계되었습니다.

## 주요 구성 요소

### Config (config.py)
- github_token : GitHub 레포 분석용 토큰
- semantic_scholar_api_key : Semantic Scholar API 키 (논문 메타데이터 검색용)
- output_dir : 결과 저장 디렉토리
- max_papers : 최대 수집 논문 수
- request_timeout : 외부 요청 타임아웃

### Input
#### 1) Research Query
- 문자열 형태의 연구 주제 또는 키워드
- 예: "NeRF based human reconstruction"

#### 2) URL 입력
- 논문 PDF URL
- GitHub Repository URL

#### 3) Config 옵션
- SEMANTIC_SCHOLAR_API_KEY
- 논문 개수 제한
- GitHub 분석 여부
- 결과 저장 형식(JSON/CSV)

### Output

#### JSON Output (r_agent_result.json)
```
{
  "stats": {
    "papers_returned": 5,
    "github_repos": 2
  },
  "papers": [
    {
      "title": "...",
      "summary": "...",
      "key_contributions": []
    }
  ]
}
```

- 모든 분석 결과를 포함하는 메인 출력 포맷
- 후처리 및 파이프라인 연계에 적합

#### CSV Output (r_agent_result.csv)
- 논문 단위 요약 결과를 테이블 형태로 저장
- 엑셀 / 구글 시트 분석에 유용
