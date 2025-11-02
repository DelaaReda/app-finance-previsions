
from __future__ import annotations
import os
from typing import Any, cast
from pathlib import Path
from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.core.indices.base import BaseIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from ..config import AgentConfig


def _ensure_embed_model() -> None:
    if Settings.embed_model is not None:
        return
    if os.getenv("OPENAI_API_KEY"):
        return
    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore
    except Exception:
        return
    model_name = os.getenv("HF_EMBED_MODEL", "intfloat/multilingual-e5-large")
    Settings.embed_model = HuggingFaceEmbedding(model_name=model_name)


def build_or_load_index(data_dir: str = "docs", cfg: AgentConfig | None = None) -> BaseIndex[Any]:
    cfg = cfg or AgentConfig()
    Path(cfg.vector_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=cfg.vector_path)
    vs = ChromaVectorStore(chroma_collection=client.get_or_create_collection("agent_docs"))
    storage = StorageContext.from_defaults(vector_store=vs)
    _ensure_embed_model()
    try:
        return cast(BaseIndex[Any], load_index_from_storage(storage))
    except Exception:
        docs = SimpleDirectoryReader(input_dir=data_dir, recursive=True).load_data()
        from llama_index.core import VectorStoreIndex
        return cast(BaseIndex[Any], VectorStoreIndex.from_documents(docs, storage_context=storage))


def query_index(q: str, topk: int = 5, data_dir: str = "docs") -> list[str]:
    idx = build_or_load_index(data_dir)
    rsp = idx.as_query_engine(similarity_top_k=topk).query(q)
    try:
        nodes = getattr(rsp, "source_nodes", [])
        out: list[str] = []
        for n in nodes:
            node = getattr(n, "node", None)
            if node is None:
                continue
            if hasattr(node, "get_text"):
                out.append(node.get_text())  # type: ignore
            elif hasattr(node, "text"):
                out.append(cast(str, node.text))
        return out or [str(rsp)]
    except Exception:
        return [str(rsp)]
