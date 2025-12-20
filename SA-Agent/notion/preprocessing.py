import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from notion.client import Notion
import os
import numpy as np
import pickle
import json
from config import LLM_CONFIG
from dotenv import load_dotenv


load_dotenv()
NOTION_TOKEN = LLM_CONFIG["notion_token"]
PAGE_ID = LLM_CONFIG["pagd_id"]
DATABASE_ID = LLM_CONFIG["database_id"]
EMBEDDING_MODEL = LLM_CONFIG["embedding_model"]

@dataclass
class Chunk:
    """ 청크 데이터 클래스 """
    text: str
    metadata: Dict[str, Any]
    chunk_id: int

class NotionTextPreprocessor:
    """ 텍스트 전처리 클래스 """
    
    def __init__(self):
        pass
    
    def clean_markdown_syntax(self, text: str) -> str:
        """ 마크다운 문법 정리 """
        # ## 헤딩을 일반 텍스트로 변환 (선택적)
        # text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # 불필요한 마크다운 기호 제거
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # bold 제거
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # italic 제거
        
        return text
    
    def normalize_lists(self, text: str) -> str:
        """ 리스트 표기 정규화 """
        # - 를 • 로 변경 (통일)
        text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
        # 1) 2) 3) 형식을 1. 2. 3. 으로 (통일)
        text = re.sub(r'^(\d+)\)\s+', r'\1. ', text, flags=re.MULTILINE)
        
        return text
    
    def remove_extra_whitespace(self, text: str) -> str:
        """ 불필요한 공백 제거 """
        # 줄 내 다중 공백을 단일 공백으로
        text = re.sub(r'[ \t]+', ' ', text)
        # 3개 이상의 연속 줄바꿈을 2개로
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 각 줄의 앞뒤 공백 제거
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def clean_special_characters(self, text: str) -> str:
        """ 특수문자 정리 """
        # Notion 특수 문자
        text = text.replace('\u200b', '')  # zero-width space
        text = text.replace('\xa0', ' ')   # non-breaking space
        text = text.replace('\u2022', '•') # bullet point 통일
        
        # 이모지 제거
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            "]+", flags=re.UNICODE)
        text = emoji_pattern.sub('', text)
        
        return text

    def preprocess(self, text: str, 
                   remove_markdown: bool = False) -> str:
        """
        전체 전처리 파이프라인
        
        Args:
            text: 원본 텍스트
            remove_markdown: 마크다운 문법 제거 여부
            remove_urls: URL 제거 여부
        """
        # 1. 특수문자 정리
        text = self.clean_special_characters(text)
        # 2. 리스트 정규화
        text = self.normalize_lists(text)
        # 3. 마크다운 정리
        if remove_markdown:
            text = self.clean_markdown_syntax(text)
        # 5. 공백 정리
        text = self.remove_extra_whitespace(text)
        
        return text


class NotionTextChunker:
    """전처리된 텍스트 청킹 클래스"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Args:
            chunk_size: 청크당 최대 문자 수
            overlap: 청크 간 겹치는 문자 수
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_by_headers(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """ 헤딩(##) 기반 청킹 - 의미 단위 보존 """
        # ## 또는 ### 등으로 섹션 분리
        sections = re.split(r'\n(?=#{1,6}\s)', text)
        
        chunks = []
        chunk_id = 0
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # 섹션이 청크 크기보다 작으면 그대로 사용
            if len(section) <= self.chunk_size:
                chunks.append(Chunk(
                    text=section,
                    metadata=metadata or {},
                    chunk_id=chunk_id
                ))
                chunk_id += 1
            else:
                # 큰 섹션은 추가 분할
                sub_chunks = self._split_section(section, metadata, chunk_id)
                chunks.extend(sub_chunks)
                chunk_id += len(sub_chunks)
        
        return chunks
    
    def _split_section(self, section: str, metadata: Dict, start_id: int) -> List[Chunk]:
        """ 큰 섹션을 문장/문단 단위로 분할 """
        # 헤딩 추출
        lines = section.split('\n')
        heading = ""
        content_start = 0
        
        if lines[0].startswith('#'):
            heading = lines[0] + "\n"
            content_start = 1
        
        content = '\n'.join(lines[content_start:])
        
        # 문단 단위로 먼저 분리 (빈 줄 기준)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = heading
        current_length = len(heading)
        chunk_id = start_id
        
        for paragraph in paragraphs:
            para_length = len(paragraph)
            
            # 청크 크기 초과 시
            if current_length + para_length > self.chunk_size and current_chunk.strip() != heading.strip():
                chunks.append(Chunk(
                    text=current_chunk.strip(),
                    metadata=metadata or {},
                    chunk_id=chunk_id
                ))
                chunk_id += 1
                
                # overlap 적용: 마지막 overlap 크기만큼 유지
                if len(current_chunk) > self.overlap:
                    overlap_text = current_chunk[-self.overlap:]
                    current_chunk = heading + overlap_text + "\n\n" + paragraph
                else:
                    current_chunk = heading + paragraph
                
                current_length = len(current_chunk)
            else:
                if current_chunk.strip() != heading.strip():
                    current_chunk += "\n\n"
                current_chunk += paragraph
                current_length += para_length + 2
        
        # 마지막 청크
        if current_chunk.strip() and current_chunk.strip() != heading.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                metadata=metadata or {},
                chunk_id=chunk_id
            ))
        
        return chunks
    


# ==================== 방법 1: LangChain 사용 (추천) ====================
class LangChainChunkingEmbedding:
    """LangChain을 사용한 청킹 및 임베딩"""
    
    def __init__(self, embedding_model="sentence-transformers/all-MiniLM-L6-v2"):
        """
        초기화
        
        Args:
            embedding_model: 사용할 임베딩 모델
                - "sentence-transformers/all-MiniLM-L6-v2" (무료, 빠름)
                - "sentence-transformers/all-mpnet-base-v2" (무료, 더 좋은 성능)
                - "openai" (유료, API 키 필요)
        """
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        self.embedding_model_name = embedding_model
        
        # 청킹 설정
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,        # 청크 크기
            chunk_overlap=50,      # 청크 간 겹침
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # 임베딩 모델 초기화
        if embedding_model.startswith("sentence-transformers"):
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model,
                model_kwargs={'device': 'cpu'},  # 'cuda' for GPU
                encode_kwargs={'normalize_embeddings': True}
            )
        else:
            raise ValueError(f"지원하지 않는 모델: {embedding_model}")
    
    def chunk_text(self, text: str) -> List[str]:
        """텍스트를 청크로 분할"""
        chunks = self.text_splitter.split_text(text)
        print(f"✂️  총 {len(chunks)}개의 청크로 분할되었습니다.")
        return chunks
    
    def embed_chunks(self, chunks: List[str]) -> np.ndarray:
        """청크들을 임베딩 벡터로 변환"""
        print(f"🔢 {len(chunks)}개 청크를 임베딩하는 중...")
        embeddings = self.embeddings.embed_documents(chunks)
        embeddings_array = np.array(embeddings)
        print(f"✅ 임베딩 완료! 벡터 크기: {embeddings_array.shape}")
        return embeddings_array
    
    def process(self, chunks: str) -> Dict:
        """전체 파이프라인: 청킹 + 임베딩"""
        # chunks = self.chunk_text(text)
        embeddings = self.embed_chunks(chunks)
        
        return {
            'chunks': chunks,
            'embeddings': embeddings,
            'model': self.embedding_model_name,
            'num_chunks': len(chunks),
            'embedding_dim': embeddings.shape[1]
        }
    
    def save(self, result: Dict, filepath: str):
        """결과 저장"""
        with open(filepath, 'wb') as f:
            pickle.dump(result, f)
        print(f"[OK] 저장 완료: {filepath}")
    
    def load(self, filepath: str) -> Dict:
        """결과 불러오기"""
        with open(filepath, 'rb') as f:
            result = pickle.load(f)
        print(f"[OK] 불러오기 완료: {filepath}")
        return result


if __name__ == "__main__":
    
    notion_client = Notion(NOTION_TOKEN)
    contents = []
    
    try:
        contents.append(notion_client.page_to_input(PAGE_ID))
    except Exception as e:
        print(f"오류 발생: {e}")

    # try:
    #     contents.append(notion_client.database_to_input(DATABASE_ID, max_pages=None))
    # except Exception as e:
    #     print(f"오류 발생: {e}")
    
    notion_text = []
    if len(contents) >= 2:
        for c in contents:
            notion_text.append(contents[c])
    
    # 전처리
    preprocessor = NotionTextPreprocessor()
    cleaned_text = preprocessor.preprocess(
        notion_text,
        remove_markdown=False  # 마크다운 유지
    )

    # 청킹
    chunker = NotionTextChunker(chunk_size=1000, overlap=50)
    chunks = chunker.chunk_by_headers(
        cleaned_text,
        metadata={"source": "notion", "page_title": "내 연구일지"}
    )
    
    # LangChain 방식 임베딩
    processor = LangChainChunkingEmbedding(
        embedding_model = EMBEDDING_MODEL # "sentence-transformers/all-MiniLM-L6-v2"
    )
    
    result = processor.process(chunks)
    
    # print(f"청크 개수: {result['num_chunks']}")
    # print(f"임베딩 차원: {result['embedding_dim']}")
    # 청크 예시
    # print(result['chunks'][i])
    
    # 결과 저장
    processor.save(result, 'embeddings.pkl')
    
    

