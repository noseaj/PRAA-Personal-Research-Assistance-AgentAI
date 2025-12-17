# Code-Aware Research Assistant (CA-Agent)

논문 메소드 기반 Github 코드와 사용자 코드를 분석하고,  
사용자 질의에 맞춰 **논문 · 레퍼런스 · 내 코드 분석 결과를 RAG 방식으로 종합**하여  
연구 및 구현 관점에서 설명해주는 **Multi-Agent 기반 Code-Aware Research Assistant**

---

## CA-Agent의 주요 시나리오
- 논문(Paper)의 **Method 섹션을 기준으로 레퍼런스 코드가 어떻게 구현되었는지 설명**
- 내 로컬 코드의 **핵심 기능과 구조 분석**
- 내 코드와 레퍼런스 코드가 **유사한 연구 문제를 다루는지 판단**
- 유사하다면 **어떤 구조적 아이디어를 참고할 수 있는지 설명**
- 모든 답변은 **분석 Agent(Reference Agent, Mycode Agent, Integration Agent) 결과에만 근거하여 생성**
- 등등..

> 단순 코드 요약이 아닌,  
> **연구 맥락을 이해한 코드 분석 및 설명**이 목표

---

## 전체 아키텍처 개요



---

## LLM 모델
- meta-llama/llama-3.1-8b-instruct

## python 버전
- 3.10