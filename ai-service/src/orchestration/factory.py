from __future__ import annotations
from pathlib import Path
from src.core.config import Settings
from infrastructure.storage.json_store import JsonProfileStore
from infrastructure.embeddings.mock import DeterministicEmbeddingProvider
from infrastructure.vector_store.local import LocalVectorStore
from infrastructure.search.trusted import MockTrustedSearch,NoWebSearch,TavilyTrustedSearch
from infrastructure.llms.mock import MockLLM
from infrastructure.llms.providers import build_provider_pool
from src.ingestion.service import IngestionService
from src.retrieval.service import RetrievalService
from src.orchestration.ai_tutor import AITutor
class UnconfiguredLLM:
    provider='unconfigured'; model='none'; is_mock=False
    def generate(self,*a,**k):raise RuntimeError('No real LLM provider is configured. Set a supported provider API key.')
    def generate_prompt(self,*a,**k):raise RuntimeError('No real LLM provider is configured. Set a supported provider API key.')

def build_system(data_dir=None,test_mode=False):
    s=Settings(); data_dir=data_dir or s.data_dir; Path(data_dir).mkdir(parents=True,exist_ok=True); store=JsonProfileStore(f'{data_dir}/profiles')
    if test_mode:
        emb=DeterministicEmbeddingProvider(); vs=LocalVectorStore(emb,f'{data_dir}/vector_db/index.json'); search=MockTrustedSearch(); providers={'mock':MockLLM()}
    else:
        if s.embedding_backend not in ('auto','sentence-transformers','mock'):raise RuntimeError(f'Unsupported embedding backend: {s.embedding_backend}')
        if s.embedding_backend=='mock':
            if not s.allow_mock_fallback:raise RuntimeError('Mock embeddings require ALLOW_MOCK_FALLBACK=true outside tests')
            emb=DeterministicEmbeddingProvider()
        else:
            try:
                from infrastructure.embeddings.real import SentenceTransformerEmbeddings; emb=SentenceTransformerEmbeddings(s.embedding_model)
            except Exception as exc:
                if not s.allow_mock_fallback:raise RuntimeError('Real embedding model failed to initialize; no silent semantic fallback is allowed') from exc
                emb=DeterministicEmbeddingProvider(); emb.name='mock-explicit-fallback'
        if s.vector_backend not in ('auto','chroma','local'):raise RuntimeError(f'Unsupported vector backend: {s.vector_backend}')
        if s.vector_backend=='local':
            if not s.allow_mock_fallback:raise RuntimeError('Local JSON vector backend is development-only; set ALLOW_MOCK_FALLBACK=true to use it')
            vs=LocalVectorStore(emb,f'{data_dir}/vector_db/index.json')
        else:
            try:
                from infrastructure.vector_store.chroma import ChromaVectorStore; vs=ChromaVectorStore(emb,s.chroma_path)
            except Exception as exc:
                if not s.allow_mock_fallback:raise RuntimeError(f'Chroma failed to initialize; no silent vector-store fallback is allowed. Original error: {type(exc).__name__}: {exc}') from exc
                vs=LocalVectorStore(emb,f'{data_dir}/vector_db/index.json'); vs.name='local-json-explicit-fallback'
        search=TavilyTrustedSearch(s.tavily_api_key,s.trust_threshold) if s.enable_web_search and s.tavily_api_key else NoWebSearch()
        providers=build_provider_pool(s.ai_provider,s.ai_model,s.fallback_providers,s.provider_keys)
        if not providers:providers={'mock':MockLLM()} if s.allow_mock_fallback else {'unconfigured':UnconfiguredLLM()}
    ret=RetrievalService(vs); ing=IngestionService(vs,f'{data_dir}/uploads',max_upload_mb=s.max_upload_mb)
    return AITutor(store,ret,ing,providers,search=search,artifact_dir=f'{data_dir}/artifacts')