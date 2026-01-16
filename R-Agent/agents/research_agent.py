import os
import re
import csv
import json
import time
import math
import tempfile
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field, ValidationError
import requests
import fitz  # PyMuPDF
from config import *

from openai import OpenAI

# =========================
# Config
# =========================

@dataclass
class AgentConfig:
    # 검색
    semantic_scholar_api_url: str = "https://api.semanticscholar.org/graph/v1"
    semantic_scholar_api_key: Optional[str] = SEMANTIC_SCHOLAR_API_KEY 

    # GitHub 분석(레포 트리 조회에 사용)
    github_token: Optional[str] = GITHUB_TOKEN

    # 동작 파라미터
    max_candidates_per_query: int = 20         # 쿼리당 논문 후보
    max_total_candidates: int = 60             # 전체 후보 상한(너무 많이 다운받지 않게)
    target_papers_with_github: int = 3         # GitHub URL 가진 논문 최소 몇 편 반환?
    sleep_between_requests: float = 1.1        # rate-limit 완화 (Semantic Scholar: 1 req/sec)
    pdf_download_timeout_sec: int = 30

    # PDF 처리
    max_pdf_pages_to_parse: int = 50           # 너무 긴 PDF 비용 제한(원하면 늘려도 됨)

    # 출력
    output_dir: str = "./output"


# =========================
# Utilities
# =========================

URL_REGEX = re.compile(r"https?://[^\s\)\]]+")
PARA_SPLIT_REGEX = re.compile(r"\n\s*\n+")

def safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def normalize_title(title: str) -> str:
    t = (title or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return t

def is_github_url(u: str) -> bool:
    return "github.com" in (u or "").lower()

def parse_github_owner_repo(repo_url: str) -> Optional[Tuple[str, str]]:
    """
    https://github.com/{owner}/{repo}[/...]
    """
    try:
        parsed = urlparse(repo_url)
        if parsed.netloc.lower() != "github.com":
            return None
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1]
        repo = repo.replace(".git", "")
        return owner, repo
    except Exception:
        return None


# =========================
# 1) Planner
# =========================

class QueryPlanner:
    """
    v0: 룰 기반 planner
    - 질문에서 영어 키워드만 추출 (한글 제거!)
    - Semantic Scholar는 영어 검색에 최적화되어 있음
    """
    def plan(self, question: str, max_queries: int = 5) -> List[str]:
        q = (question or "").strip()
        if not q:
            return []

        # 영어/숫자만 추출 (한글 제거! - Semantic Scholar 호환성)
        english_tokens = re.findall(r"[A-Za-z][A-Za-z0-9]*", q)
        # 대소문자 유지 (DETR, ResNet 등 고유명사 보존)
        english_tokens = [t for t in english_tokens if len(t) >= 2]
        english_tokens = english_tokens[:8]  # 과도한 길이 제한

        # 영어 토큰이 없으면 원본에서 영어만 추출 시도
        if not english_tokens:
            # 숫자+영어 조합도 허용
            english_tokens = re.findall(r"[A-Za-z0-9]+", q)
            english_tokens = [t for t in english_tokens if re.search(r"[A-Za-z]", t)]

        base = " ".join(english_tokens) if english_tokens else q

        # 확장 쿼리 (영어만 사용)
        queries = [
            base,
            f"{base} deep learning",
            f"{base} neural network github",
            f"{base} machine learning code",
            f"{base} paper implementation",
        ]

        # 중복 제거 + 길이 제한
        seen = set()
        out = []
        for x in queries:
            x = x.strip()
            if not x:
                continue
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
            if len(out) >= max_queries:
                break

        return out


# =========================
# 2) Paper Search (Semantic Scholar)
# =========================

class SemanticScholarClient:
    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {}
        if self.cfg.semantic_scholar_api_key:
            h["x-api-key"] = self.cfg.semantic_scholar_api_key
        return h

    def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Graph API: /paper/search
        """
        params = {
            "query": query,
            "limit": limit,
            "fields": ",".join([
                "title",
                "year",
                "venue",
                "paperId",
                "url",
                "abstract",
                "authors",
                "citationCount",
                "openAccessPdf",
                "externalIds",
            ]),
        }
        r = requests.get(
            f"{self.cfg.semantic_scholar_api_url}/paper/search",
            params=params,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("data", [])


# =========================
# 3) PDF Extractors (GitHub links + paragraphs)
# =========================

def download_pdf(url: str, dest_path: str, timeout_sec: int) -> bool:
    try:
        with requests.get(url, stream=True, timeout=timeout_sec) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception:
        return False

def extract_text_from_pdf(pdf_path: str, max_pages: int) -> str:
    doc = fitz.open(pdf_path)
    texts = []
    n = min(len(doc), max_pages)
    for i in range(n):
        texts.append(doc[i].get_text())
    doc.close()
    return "\n".join(texts)

def split_into_paragraphs(text: str) -> List[str]:
    paras = [p.strip() for p in PARA_SPLIT_REGEX.split(text or "") if p.strip()]
    return paras

def extract_github_links_with_paragraph_context(text: str) -> List[Dict[str, Any]]:
    """
    문단 단위로 GitHub URL 추출 + 해당 문단 전체 context.
    """
    paras = split_into_paragraphs(text)
    seen = set()
    out = []
    for p in paras:
        for m in URL_REGEX.finditer(p):
            url = m.group(0).rstrip(".,);")
            if not is_github_url(url):
                continue
            if url in seen:
                continue
            seen.add(url)
            out.append({
                "url": url,
                "context": p.replace("\n", " ").strip(),
                "role_summary": None,
                "repo_summary": None,  # repo analyzer가 채움
            })
    return out


# =========================
# 4) Summarizers (짧은 요약 / 코드 역할 요약)
# =========================

class Summarizer:
    """
    LLM 기반 논문 분석 요약기
    """
    def __init__(self, llm_client: OpenAI = None, model: str = "anthropic/claude-sonnet-4"):
        self.llm_client = llm_client
        self.model = model

    def short_summary_from_abstract(self, abstract: str) -> Dict[str, str]:
        """
        LLM을 사용하여 논문 초록 분석
        """
        abs_t = (abstract or "").strip()
        if not abs_t:
            return {
                "problem": "",
                "method": "",
                "strength": "",
            }
        
        # LLM이 있으면 사용
        if self.llm_client:
            try:
                prompt = f"""다음 논문 초록을 분석하여 JSON 형식으로 요약해주세요.

초록:
{abs_t[:2000]}

다음 형식의 JSON만 출력:
{{
    "problem": "이 논문이 해결하려는 문제 (1-2문장)",
    "method": "제안하는 방법/핵심 기여 (1-2문장)",
    "strength": "장점 또는 실험 결과 (1-2문장)"
}}"""
                
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=500
                )
                
                result_text = response.choices[0].message.content.strip()
                json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            except Exception as e:
                print(f"[Summarizer] LLM 요약 실패: {e}")
        
        # Fallback: 규칙 기반
        sents = re.split(r"(?<=[.!?])\s+", abs_t)
        sents = [s.strip() for s in sents if s.strip()]
        return {
            "problem": sents[0] if len(sents) >= 1 else "",
            "method": sents[1] if len(sents) >= 2 else "",
            "strength": sents[2] if len(sents) >= 3 else "",
        }
    
    def analyze_paper(self, title: str, abstract: str, authors: List[str] = None) -> str:
        """
        논문 전체 분석 (LLM 기반)
        """
        if not self.llm_client:
            return ""
        
        try:
            prompt = f"""다음 논문을 분석하여 한국어로 요약해주세요.

제목: {title}
저자: {', '.join(authors[:5]) if authors else 'N/A'}
초록: {(abstract or '')[:2000]}

다음 형식으로 분석:
1. **핵심 아이디어**: 이 논문의 주요 기여는 무엇인가요? (2-3문장)
2. **기술적 접근**: 어떤 방법론/아키텍처를 사용하나요? (2-3문장)
3. **연구 의의**: 이 연구가 중요한 이유는? (1-2문장)
4. **활용 가능성**: 어떤 분야/문제에 적용할 수 있나요? (1-2문장)"""
            
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Summarizer] 논문 분석 실패: {e}")
            return ""

    def summarize_code_role(self, context_paragraph: str, paper_title: str = "") -> str:
        """
        URL이 포함된 문단(context) 기반으로 '이 코드가 어떤 역할인지' 1~2문장 요약.
        """
        c = (context_paragraph or "").lower()
        hints = []
        if "code" in c or "implementation" in c:
            hints.append("구현 코드")
        if "pretrained" in c or "checkpoint" in c or "model" in c:
            hints.append("모델/체크포인트")
        if "reproduce" in c or "reproduc" in c:
            hints.append("재현성/재실험")
        if "dataset" in c or "data" in c:
            hints.append("데이터/전처리")

        if hints:
            return f"논문에서 공개한 {', '.join(sorted(set(hints)))}를 제공하는 레포로 보입니다."
        return "논문에서 제안한 방법 또는 실험 재현을 위한 공개 레포로 보입니다."
    
    def generate_overall_analysis(self, papers: List[Dict], question: str) -> str:
        """
        검색된 논문들에 대한 종합 분석 생성
        """
        if not self.llm_client or not papers:
            return ""
        
        try:
            paper_summaries = []
            for i, p in enumerate(papers[:5], 1):
                paper_summaries.append(f"""
{i}. {p.get('title', 'N/A')} ({p.get('year', 'N/A')})
   - 초록: {(p.get('abstract') or '')[:300]}...
   - GitHub: {p.get('code', [{}])[0].get('repo_url', 'N/A') if p.get('code') else 'N/A'}""")
            
            papers_text = "\n".join(paper_summaries)
            
            prompt = f"""사용자 질문: {question}

검색된 논문들:
{papers_text}

위 논문들을 바탕으로 다음을 포함한 종합 분석을 작성해주세요 (한국어):

## 📊 검색 결과 요약
- 검색된 논문 수와 주요 특징

## 🔬 연구 동향 분석
- 이 분야의 주요 접근 방법들
- 최근 연구 트렌드

## 💡 추천 순위
- 가장 참고할 만한 논문 순위와 이유

## 🔗 GitHub 코드 활용
- 코드가 공개된 논문과 활용 방법"""
            
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Summarizer] 종합 분석 실패: {e}")
            return ""


# =========================
# 5) Repo Analyzer (GitHub API 기반)
# =========================

class GitHubRepoAnalyzer:
    """
    v0: clone 없이 GitHub API로 tree/README를 보고
    - 주요 폴더/파일 후보를 규칙 기반으로 뽑아준다.
    - 논문 제목으로 GitHub 레포 검색 기능 추가
    """
    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json"}
        if self.cfg.github_token:
            h["Authorization"] = f"Bearer {self.cfg.github_token}"
        return h
    
    def search_repo_by_paper(self, paper_title: str, authors: List[str] = None) -> Optional[str]:
        """
        논문 제목으로 GitHub 레포지토리 검색 (GitHub Search API)
        
        Args:
            paper_title: 논문 제목
            authors: 저자 목록 (선택)
            
        Returns:
            가장 관련성 높은 GitHub URL 또는 None
        """
        try:
            # 1. 논문 제목에서 핵심 키워드/약어 추출 (DETR, BERT, GPT 등)
            acronyms = re.findall(r'\b[A-Z]{2,}[a-z]*\b', paper_title)  # DETR, BERT 등
            
            # 2. 여러 검색 쿼리 시도 (약어 우선)
            search_queries = []
            
            # 약어가 있으면 약어로 먼저 검색
            if acronyms:
                search_queries.append(" ".join(acronyms))
            
            # 전체 제목 검색
            search_queries.append(paper_title)
            
            # 핵심 키워드만 검색 (detection, transformer 등)
            key_words = [w for w in re.findall(r'\b\w+\b', paper_title.lower()) 
                        if len(w) >= 4 and w not in ['with', 'from', 'using', 'based', 'end-to-end', 'towards']]
            if key_words:
                search_queries.append(" ".join(key_words[:5]))
            
            url = "https://api.github.com/search/repositories"
            
            for query in search_queries:
                params = {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10
                }
                
                r = requests.get(url, params=params, headers=self._headers(), timeout=15)
                time.sleep(self.cfg.sleep_between_requests)
                
                if r.status_code != 200:
                    continue
                
                data = r.json()
                items = data.get("items", [])
                
                # 가장 관련성 높은 레포 찾기
                for item in items:
                    repo_name = item.get("name", "").lower()
                    repo_desc = (item.get("description") or "").lower()
                    full_name = item.get("full_name", "").lower()
                    stars = item.get("stargazers_count", 0)
                    
                    # 논문 약어가 레포 이름에 정확히 포함되어 있는지 (DETR → detr)
                    acronym_match = any(acr.lower() in repo_name for acr in acronyms)
                    
                    # 유명 AI 연구 기관 레포인지 확인
                    trusted_orgs = ['facebookresearch', 'google', 'huggingface', 'openai', 
                                   'microsoft', 'pytorch', 'tensorflow', 'nvidia', 'meta-llama']
                    from_trusted = any(org in full_name for org in trusted_orgs)
                    
                    # 선택 기준:
                    # 1. 약어가 레포 이름에 있고 스타 500개 이상
                    # 2. 신뢰 기관 레포이고 스타 1000개 이상
                    # 3. 스타 5000개 이상
                    if (acronym_match and stars >= 500) or \
                       (from_trusted and stars >= 1000) or \
                       (stars >= 5000):
                        print(f"[GitHub Search] 매칭: {item.get('html_url')} (⭐{stars})")
                        return item.get("html_url")
            
            return None
            
        except Exception as e:
            print(f"[GitHub Search] 검색 실패: {e}")
            return None

    def get_default_branch(self, owner: str, repo: str) -> Optional[str]:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        r = requests.get(url, headers=self._headers(), timeout=20)
        if r.status_code != 200:
            return None
        return r.json().get("default_branch")

    def get_tree_recursive(self, owner: str, repo: str, branch: str) -> Optional[List[Dict[str, Any]]]:
        """
        GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
        r = requests.get(url, headers=self._headers(), params={"recursive": "1"}, timeout=20)
        if r.status_code != 200:
            return None
        return r.json().get("tree")

    def summarize_repo_structure(self, repo_url: str) -> Optional[Dict[str, Any]]:
        parsed = parse_github_owner_repo(repo_url)
        if not parsed:
            return None
        owner, repo = parsed

        branch = self.get_default_branch(owner, repo) or "main"
        tree = self.get_tree_recursive(owner, repo, branch)
        if not tree:
            return None

        paths = [x.get("path") for x in tree if x.get("type") in ("blob", "tree") and x.get("path")]
        files = [p for p in paths if not p.endswith("/")]
        dirs = sorted({p.split("/")[0] for p in paths if "/" in p})

        # 규칙 기반 key paths 탐지
        key_patterns = [
            r"(^|/)models(/|$)",
            r"(^|/)model(/|$)",
            r"(^|/)datasets?(/|$)",
            r"(^|/)data(/|$)",
            r"(^|/)dataloader(s)?(/|$)",
            r"(^|/)configs?(/|$)",
            r"(^|/)scripts?(/|$)",
            r"(^|/)trainer(s)?(/|$)",
            r"(^|/)train\.py$",
            r"(^|/)training\.py$",
            r"(^|/)run\.py$",
            r"(^|/)main\.py$",
            r"(^|/)inference\.py$",
            r"(^|/)predict\.py$",
            r"(^|/)requirements\.txt$",
            r"(^|/)environment\.yml$",
            r"(^|/)pyproject\.toml$",
            r"(^|/)setup\.py$",
            r"(^|/)README(\.md)?$",
        ]
        key_regex = re.compile("|".join(f"({p})" for p in key_patterns), re.IGNORECASE)

        key_paths = []
        for p in paths:
            if key_regex.search(p):
                key_paths.append(p)
        key_paths = sorted(set(key_paths))[:40]  # 과도한 출력 제한

        # entrypoints 추정
        entry_candidates = [p for p in files if re.search(r"(train|run|main|inference|predict)\.py$", p, re.IGNORECASE)]
        entry_candidates = sorted(set(entry_candidates))[:15]

        # 간단 ML stack 추정(파일/폴더명 기반)
        stack_guess = []
        joined = "\n".join(files).lower()
        if "torch" in joined or "pytorch" in joined:
            stack_guess.append("pytorch")
        if "tensorflow" in joined or "tf" in joined:
            stack_guess.append("tensorflow")
        if "jax" in joined:
            stack_guess.append("jax")
        if "lightning" in joined or "pytorch_lightning" in joined:
            stack_guess.append("pytorch-lightning")

        return {
            "owner": owner,
            "repo": repo,
            "default_branch": branch,
            "top_dirs": dirs[:30],
            "entrypoints": entry_candidates,
            "key_paths": key_paths,
            "ml_stack_guess": stack_guess,
        }


# =========================
# 6) R-Agent Orchestrator
# =========================

class RAgent:
    def __init__(self, cfg: AgentConfig, llm_client: OpenAI = None):
        self.cfg = cfg
        self.planner = QueryPlanner()
        self.s2 = SemanticScholarClient(cfg)
        self.llm_client = llm_client
        self.summarizer = Summarizer(llm_client=llm_client)
        self.repo_analyzer = GitHubRepoAnalyzer(cfg)

    def run(self, question: str, external_keywords: list = None) -> Dict[str, Any]:
        """
        R-Agent 실행
        
        Args:
            question: 연구 질문 (원본)
            external_keywords: O-Agent에서 LLM이 추출한 영어 키워드 목록 (Optional)
                              제공되면 QueryPlanner 대신 이 키워드 사용
        """
        safe_mkdir(self.cfg.output_dir)

        # 1) Plan queries
        # 외부 키워드가 제공되면 우선 사용 (LLM이 추출한 영어 키워드)
        if external_keywords and len(external_keywords) > 0:
            print(f"[R-Agent] 외부 키워드 사용: {external_keywords}")
            # 외부 키워드 기반 쿼리 생성
            base = " ".join(external_keywords)
            queries = [
                base,
                f"{base} deep learning",
                f"{base} github code",
                f"{base} neural network",
                f"{base} implementation",
            ][:5]
        else:
            # 기존 QueryPlanner 사용
            queries = self.planner.plan(question, max_queries=5)

        # 2) Collect candidates from multiple queries
        candidates: List[Dict[str, Any]] = []
        for q in queries:
            batch = self.s2.search(q, limit=self.cfg.max_candidates_per_query)
            candidates.extend(batch)
            time.sleep(self.cfg.sleep_between_requests)

            if len(candidates) >= self.cfg.max_total_candidates:
                break

        # 3) Deduplicate + rank
        dedup = self._dedup_candidates(candidates)
        ranked = self._rank_candidates(dedup)

        # 4) Process papers until we have enough "papers with github"
        results: List[Dict[str, Any]] = []
        scanned = 0
        for paper in ranked:
            if len(results) >= self.cfg.target_papers_with_github:
                break
            scanned += 1

            processed = self._process_single_paper(paper)
            if processed is None:
                continue

            # GitHub URL ≥ 1개인 논문만 포함
            if processed.get("code") and len(processed["code"]) > 0:
                results.append(processed)
        
        # 5) 각 논문에 대한 LLM 상세 분석 추가
        for paper in results:
            analysis = self.summarizer.analyze_paper(
                title=paper.get("title", ""),
                abstract=paper.get("abstract", ""),
                authors=paper.get("authors", [])
            )
            paper["llm_analysis"] = analysis
        
        # 6) 종합 분석 생성
        overall_analysis = self.summarizer.generate_overall_analysis(results, question)

        return {
            "agent": "R-Agent (Ref Researcher)",
            "input_question": question,
            "generated_queries": queries,
            "overall_analysis": overall_analysis,  # 종합 분석 추가
            "results": results,
            "stats": {
                "candidates_collected": len(candidates),
                "candidates_deduped": len(dedup),
                "papers_scanned_ranked": scanned,
                "papers_returned": len(results),
                "repos_analyzed": sum(len(x.get("code", [])) for x in results),
            }
        }

    # ---------- internals ----------

    def _dedup_candidates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for p in papers:
            title = normalize_title(p.get("title", ""))
            pid = p.get("paperId")
            key = pid or title
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    def _rank_candidates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        간단 랭킹:
        - citationCount 가산
        - 최근년도 가산
        - openAccessPdf 있으면 가산
        - abstract 있으면 가산(요약하기 쉬움)
        """
        def score(p: Dict[str, Any]) -> float:
            year = p.get("year") or 0
            cit = p.get("citationCount") or 0
            has_pdf = 1 if (p.get("openAccessPdf") or {}).get("url") else 0
            has_abs = 1 if p.get("abstract") else 0
            # 너무 극단적으로 치우치지 않게 log
            return (math.log1p(cit) * 2.0) + (0.2 * max(0, year - 2000)) + (2.0 * has_pdf) + (0.5 * has_abs)
        return sorted(papers, key=score, reverse=True)

    def _process_single_paper(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        title = paper.get("title")
        year = paper.get("year")
        venue = paper.get("venue")
        paper_id = paper.get("paperId")
        s2_url = paper.get("url")
        abstract = paper.get("abstract") or ""

        authors = []
        for a in (paper.get("authors") or []):
            n = a.get("name")
            if n:
                authors.append(n)

        pdf_url = ((paper.get("openAccessPdf") or {}).get("url")) if paper.get("openAccessPdf") else None

        # 1) short summary (abstract 기반)
        short_summary = self.summarizer.short_summary_from_abstract(abstract)

        # 2) pdf에서 github 링크 추출(가능하면)
        github_items: List[Dict[str, Any]] = []
        evidence_paras: List[str] = []

        if pdf_url:
            with tempfile.TemporaryDirectory() as tmpdir:
                pdf_path = os.path.join(tmpdir, "paper.pdf")
                ok = download_pdf(pdf_url, pdf_path, timeout_sec=self.cfg.pdf_download_timeout_sec)
                time.sleep(self.cfg.sleep_between_requests)
                if ok:
                    text = extract_text_from_pdf(pdf_path, max_pages=self.cfg.max_pdf_pages_to_parse)
                    gh = extract_github_links_with_paragraph_context(text)
                    github_items = gh
                    evidence_paras = [x["context"] for x in gh[:5]]  # 근거 문단 일부만

        # 3) GitHub 링크가 있다면 role_summary + repo 구조 요약
        code_blocks = []
        for item in github_items:
            repo_url = item["url"]
            context = item["context"]

            role_summary = self.summarizer.summarize_code_role(context, paper_title=title or "")
            repo_summary = self.repo_analyzer.summarize_repo_structure(repo_url)

            code_blocks.append({
                "kind": "github",
                "repo_url": repo_url,
                "source": "paper_pdf_text",
                "context_paragraph": context,
                "role_summary": role_summary,
                "repo_summary": repo_summary,
            })
            time.sleep(self.cfg.sleep_between_requests)
        
        # 4) PDF에서 GitHub을 못 찾았으면 GitHub 검색 API로 시도
        if not code_blocks and title:
            print(f"[R-Agent] PDF에서 GitHub 없음, GitHub Search API 시도: {title[:50]}...")
            searched_url = self.repo_analyzer.search_repo_by_paper(title, authors)
            
            if searched_url:
                print(f"[R-Agent] ✅ GitHub 검색 성공: {searched_url}")
                repo_summary = self.repo_analyzer.summarize_repo_structure(searched_url)
                code_blocks.append({
                    "kind": "github",
                    "repo_url": searched_url,
                    "source": "github_search_api",  # PDF가 아닌 검색으로 찾음
                    "context_paragraph": f"논문 '{title}'과 관련된 GitHub 레포지토리로 검색됨",
                    "role_summary": "GitHub 검색 API를 통해 찾은 관련 레포지토리입니다.",
                    "repo_summary": repo_summary,
                })
                time.sleep(self.cfg.sleep_between_requests)

        result = {
            "type": "paper",
            "title": title,
            "year": year,
            "venue": venue,
            "authors": authors,
            "paper_url": s2_url,
            "pdf_url": pdf_url,
            "paperId": paper_id,
            "short_summary": short_summary,
            "evidence": {
                "code_mention_paragraphs": evidence_paras,
            },
            "code": code_blocks,
        }
        # print(result)

        return result


# =========================
# 7) Output helpers (CSV)
# =========================

def save_results_to_csv(agent_output: Dict[str, Any], csv_path: str) -> None:
    """
    GitHub 레포 1개당 1행(row)로 저장
    """
    rows = []
    for r in agent_output.get("results", []):
        base = {
            "paper_title": r.get("title"),
            "year": r.get("year"),
            "venue": r.get("venue"),
            "paper_url": r.get("paper_url"),
            "pdf_url": r.get("pdf_url"),
        }
        for c in r.get("code", []):
            repo_summary = c.get("repo_summary") or {}
            rows.append({
                **base,
                "repo_url": c.get("repo_url"),
                "role_summary": c.get("role_summary"),
                "context_paragraph": c.get("context_paragraph"),
                "entrypoints": "; ".join(repo_summary.get("entrypoints") or []),
                "key_paths": "; ".join(repo_summary.get("key_paths") or []),
                "top_dirs": "; ".join(repo_summary.get("top_dirs") or []),
                "ml_stack_guess": "; ".join(repo_summary.get("ml_stack_guess") or []),
            })

    safe_mkdir(os.path.dirname(csv_path) or ".")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "paper_title","year","venue","paper_url","pdf_url",
            "repo_url","role_summary","context_paragraph",
            "entrypoints","key_paths","top_dirs","ml_stack_guess"
        ])
        writer.writeheader()
        writer.writerows(rows)


# =========================
# 8) main
# =========================

if __name__ == "__main__":
    cfg = AgentConfig(output_dir="./output")

    question = "object tracking sports"
    agent = RAgent(cfg)
    out = agent.run(question)

    # JSON 저장
    safe_mkdir(cfg.output_dir)
    json_path = os.path.join(cfg.output_dir, "r_agent_result.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # CSV 저장(옵션)
    csv_path = os.path.join(cfg.output_dir, "r_agent_result.csv")
    save_results_to_csv(out, csv_path)

    print(f"[OK] JSON saved: {json_path}")
    print(f"[OK] CSV saved:  {csv_path}")
    print(f"[OK] Returned papers: {out['stats']['papers_returned']}")
