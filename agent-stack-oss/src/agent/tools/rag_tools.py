
from __future__ import annotations
from pathlib import Path
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from ..config import AgentConfig
def build_or_load_index(data_dir: str = "docs", cfg: AgentConfig | None = None) -> VectorStoreIndex:
    cfg = cfg or AgentConfig()
    Path(cfg.vector_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=cfg.vector_path)
    vs = ChromaVectorStore(chroma_collection=client.get_or_create_collection("agent_docs"))
    storage = StorageContext.from_defaults(vector_store=vs)
    try:
        return load_index_from_storage(storage)
    except Exception:
        docs = SimpleDirectoryReader(input_dir=data_dir, recursive=True).load_data()
        return VectorStoreIndex.from_documents(docs, storage_context=storage)
def query_index(q: str, topk: int = 5, data_dir: str = "docs") -> list[str]:
    idx = build_or_load_index(data_dir)
    rsp = idx.as_query_engine(similarity_top_k=topk).query(q)
    if hasattr(rsp, 'source_nodes'):
        return [n.node.get_text() for n in rsp.source_nodes]
    return [str(rsp)]
