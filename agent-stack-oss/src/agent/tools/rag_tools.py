
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
    # Avoid triggering default OpenAI resolution by not reading Settings.embed_model first.
    if os.getenv("OPENAI_API_KEY"):
        return
    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore
        model_name = os.getenv("HF_EMBED_MODEL", "intfloat/multilingual-e5-large-instruct")
        Settings.embed_model = HuggingFaceEmbedding(model_name=model_name)
        try:
            Settings.llm = None  # type: ignore[assignment]
        except Exception:
            pass
    except Exception:
        # If HF not available, leave defaults (retrieval may still fall back to sampling)
        return


def build_or_load_index(data_dir: str = "docs", cfg: AgentConfig | None = None) -> BaseIndex[Any]:
    cfg = cfg or AgentConfig()
    Path(cfg.vector_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=cfg.vector_path)
    # Collection name tied to source directory to prevent rebuild thrash
    import hashlib as _hashlib
    dir_key = _hashlib.sha1(str(Path(data_dir).resolve()).encode("utf-8")).hexdigest()[:8]
    coll_name = f"agent_docs_{dir_key}"
    collection = client.get_or_create_collection(coll_name)
    vs = ChromaVectorStore(chroma_collection=collection)
    storage = StorageContext.from_defaults(vector_store=vs)
    _ensure_embed_model()
    # Rebuild when empty or stale
    meta = Path(cfg.vector_path) / f".last_index_{dir_key}"
    def _docs_mtime(root: Path) -> float:
        latest = 0.0
        if not root.exists():
            return latest
        for fp in root.rglob("*"):
            try:
                latest = max(latest, fp.stat().st_mtime)
            except Exception:
                continue
        return latest
    need_rebuild = False
    try:
        if collection.count() == 0:  # type: ignore[attr-defined]
            need_rebuild = True
    except Exception:
        need_rebuild = True
    if not need_rebuild:
        try:
            idx_time = meta.stat().st_mtime if meta.exists() else 0.0
            if _docs_mtime(Path(data_dir)) > idx_time:
                need_rebuild = True
        except Exception:
            need_rebuild = True
    if need_rebuild:
        if os.getenv("AGENT_DEBUG"):
            print(f"[rag] (re)building index for {data_dir} into collection {coll_name}")
        docs = SimpleDirectoryReader(input_dir=data_dir, recursive=True).load_data()
        from llama_index.core import VectorStoreIndex
        idx = cast(BaseIndex[Any], VectorStoreIndex.from_documents(docs, storage_context=storage))
        try:
            meta.write_text("indexed", encoding="utf-8")
        except Exception:
            pass
        return idx
    if os.getenv("AGENT_DEBUG"):
        try:
            print(f"[rag] using collection {coll_name}, count={collection.count()}")
        except Exception:
            pass
    try:
        return cast(BaseIndex[Any], load_index_from_storage(storage))
    except Exception:
        # If no persisted index in storage, rebuild from documents
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
        if not out:
            base = Path(data_dir)
            samples: list[str] = []
            for p in sorted(base.rglob("*.md"))[:topk]:
                try:
                    samples.append(p.read_text(encoding="utf-8")[:4000])
                except Exception:
                    continue
            if os.getenv("AGENT_DEBUG"):
                print(f"[rag] sampled {len(samples)} files from {data_dir}")
            if samples:
                return samples
        return out or [str(rsp)]
    except Exception:
        return [str(rsp)]
