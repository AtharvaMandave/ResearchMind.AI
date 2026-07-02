"""
ResearchMind AI – LLM & Embeddings Singletons
Uses Groq (Llama3 70B) for LLM and sentence-transformers for local embeddings.
"""
import logging
from functools import lru_cache

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Cached Groq LLM singleton (Llama3 70B)."""
    settings = get_settings()
    logger.info("[LLM] Initialising Groq ChatGroq with model: %s", settings.llm_model)
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0.2,
        max_tokens=4096,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Cached sentence-transformers embeddings singleton (all-MiniLM-L6-v2, 384 dims)."""
    settings = get_settings()
    logger.info("[Embeddings] Loading model: %s", settings.embedding_model)
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
