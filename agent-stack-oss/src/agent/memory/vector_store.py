
from __future__ import annotations
import os
import hashlib
from typing import Iterable, Any, cast
import chromadb
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import InMemoryStore
from langchain_community.embeddings import HuggingFaceEmbeddings, OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain.embeddings.base import Embeddings
from pydantic import SecretStr
from ..config import AgentConfig
class VectorMemory:
    def __init__(self, cfg: AgentConfig | None = None):
        self.cfg = cfg or AgentConfig()
        self.client = chromadb.PersistentClient(path=self.cfg.vector_path)
        self.col = self.client.get_or_create_collection("agent_mem")
        base: Embeddings
        if self.cfg.provider == "ollama":
            base = OllamaEmbeddings(model=self.cfg.ollama_model, base_url=self.cfg.ollama_base_url)
        elif self.cfg.provider == "g4f" or not self.cfg.openai_api_key:
            model_name = os.getenv("HF_EMBED_MODEL", "intfloat/multilingual-e5-large-instruct")
            base = HuggingFaceEmbeddings(model_name=model_name)
        else:
            base = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=SecretStr(self.cfg.openai_api_key) if self.cfg.openai_api_key else None,
                base_url=self.cfg.openai_base_url or None,
            )
        self.emb = CacheBackedEmbeddings.from_bytes_store(base, InMemoryStore())
    def _id(self, text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()
    def upsert_texts(self, texts: Iterable[str], meta: dict | None = None):
        texts = list(texts)
        if not texts:
            return
        embs = self.emb.embed_documents(texts)
        ids = [self._id(t) for t in texts]
        metas: list[dict[str, Any]] = [cast(dict[str, Any], meta or {}) for _ in texts]
        self.col.upsert(
            ids=ids,
            documents=texts,
            metadatas=cast(Any, metas),
            embeddings=cast(Any, embs),
        )
    def search(self, query: str, k: int = 8) -> list[dict]:
        q_emb = self.emb.embed_query(query)
        res = cast(Any, self.col.query(query_embeddings=[cast(Any, q_emb)], n_results=k))
        out: list[dict[str, Any]] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[None]])[0]
        for i in range(len(ids)):
            out.append({"id": ids[i], "text": docs[i], "meta": metas[i], "distance": dists[i]})
        return out
