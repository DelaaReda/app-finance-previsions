
from __future__ import annotations
import hashlib
from typing import Iterable
import chromadb
from langchain.embeddings import CacheBackedEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from langchain.storage import InMemoryStore
from ..config import AgentConfig
class VectorMemory:
    def __init__(self, cfg: AgentConfig | None = None):
        self.cfg = cfg or AgentConfig()
        self.client = chromadb.PersistentClient(path=self.cfg.vector_path)
        self.col = self.client.get_or_create_collection("agent_mem")
        if self.cfg.provider == "ollama":
            base = OllamaEmbeddings(model=self.cfg.ollama_model, base_url=self.cfg.ollama_base_url)
        else:
            base = OpenAIEmbeddings(model="text-embedding-3-small", api_key=self.cfg.openai_api_key, base_url=self.cfg.openai_base_url or None)
        self.emb = CacheBackedEmbeddings.from_bytes_store(base, InMemoryStore())
    def _id(self, text: str) -> str:
        import hashlib
        return hashlib.sha1(text.encode("utf-8")).hexdigest()
    def upsert_texts(self, texts: Iterable[str], meta: dict | None = None):
        texts = list(texts)
        if not texts: return
        embs = self.emb.embed_documents(texts)
        ids = [self._id(t) for t in texts]
        metas = [meta or {} for _ in texts]
        self.col.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embs)
    def search(self, query: str, k: int = 8) -> list[dict]:
        q_emb = self.emb.embed_query(query)
        res = self.col.query(query_embeddings=[q_emb], n_results=k)
        out = []
        for i in range(len(res.get("ids", [[]])[0])):
            out.append({"id": res["ids"][0][i], "text": res["documents"][0][i], "meta": res["metadatas"][0][i], "distance": res.get("distances", [[None]])[0][i]})
        return out
