"""
Copilot Conversation History - Message thread storage for follow-up Q&A

Stores conversation threads with:
- conversation_id, created_at, updated_at
- Messages with role (user/assistant), content, timestamp, metadata
- Context inheritance (tickers, scope, portfolio)
- Follow-up chain tracking

BATCH-73-DEV-02: Interactive Q&A flow with conversation history
Deliverable: conversation storage + follow-up question support
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from storage.io import load_json, save_json
except Exception:
    load_json = None  # type: ignore
    save_json = None  # type: ignore

# Storage keys
CONVERSATION_HISTORY_STORAGE_KEY = "copilot_conversation_history"
CONVERSATION_SCHEMA_VERSION = "copilot_conversation_v1"

# Storage paths
_conversations_dir_cache: Optional[Path] = None


def _get_conversations_dir() -> Path:
    """Get or create conversations directory."""
    global _conversations_dir_cache
    if _conversations_dir_cache is not None:
        return _conversations_dir_cache

    override = str(os.getenv("COPILOT_CONVERSATIONS_DIR") or "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        _conversations_dir_cache = path
        return path

    # Fallback to runtime/data directory
    try:
        from platform.legacy.core.path_resolver import get_data_directory
        base_dir = get_data_directory()
    except Exception:
        base_dir = Path(__file__).resolve().parents[5] / "runtime" / "data"

    path = base_dir / "copilot_conversations"
    path.mkdir(parents=True, exist_ok=True)
    _conversations_dir_cache = path
    return path


def _conversation_index_path() -> Path:
    """Get path to conversation index file."""
    return _get_conversations_dir() / "index.json"


def _conversation_entry_path(conversation_id: str) -> Path:
    """Get path for a specific conversation entry."""
    return _get_conversations_dir() / "threads" / f"{conversation_id}.json"


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _generate_conversation_id(first_question: str, tickers: Optional[List[str]] = None) -> str:
    """Generate unique conversation ID from first question + scope + timestamp."""
    timestamp = _utc_now_iso()
    tickers_str = ",".join(sorted(tickers or []))
    content = f"{first_question}|{tickers_str}|{timestamp}"
    return sha1(content.encode()).hexdigest()[:16]


def _normalize_tickers(tickers: Optional[List[str]]) -> List[str]:
    """Normalize ticker list."""
    normalized: List[str] = []
    seen = set()
    for item in tickers or []:
        token = str(item).strip().upper()
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


def _load_conversation_index() -> Dict[str, Any]:
    """Load conversation index."""
    if load_json is None:
        return {"conversations": [], "count": 0}
    try:
        return load_json(CONVERSATION_HISTORY_STORAGE_KEY) or {"conversations": [], "count": 0}
    except Exception:
        return {"conversations": [], "count": 0}


def _save_conversation_index(index: Dict[str, Any]) -> Optional[Path]:
    """Save conversation index."""
    if save_json is None:
        return None
    try:
        index_path = _conversation_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        return save_json(CONVERSATION_HISTORY_STORAGE_KEY, index)
    except Exception:
        return None


def _load_conversation_thread(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific conversation thread."""
    if load_json is None:
        return None
    try:
        entry_path = _conversation_entry_path(conversation_id)
        if not entry_path.exists():
            return None
        with open(entry_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def _save_conversation_thread(conversation_id: str, thread: Dict[str, Any]) -> Optional[Path]:
    """Save a conversation thread."""
    try:
        entry_path = _conversation_entry_path(conversation_id)
        # Ensure threads directory exists
        threads_dir = _get_conversations_dir() / "threads"
        threads_dir.mkdir(parents=True, exist_ok=True)
        with open(entry_path, 'w') as f:
            json.dump(thread, f, indent=2, default=str)
        return entry_path
    except Exception as exc:
        return None


def create_conversation(
    *,
    first_question: str,
    tickers: Optional[List[str]] = None,
    scope: Optional[Dict[str, Any]] = None,
    portfolio_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a new conversation thread.

    Args:
        first_question: Opening user question
        tickers: Related tickers for context
        scope: Additional scope (portfolio_id, etc.)
        portfolio_id: Saved portfolio reference
        metadata: Additional metadata

    Returns:
        Conversation metadata with conversation_id
    """
    now_iso = _utc_now_iso()
    normalized_tickers = _normalize_tickers(tickers)
    conversation_id = _generate_conversation_id(first_question, normalized_tickers)

    # Build initial message
    user_message = {
        "message_id": "msg_001",
        "role": "user",
        "content": first_question,
        "timestamp": now_iso,
        "metadata": {
            "tickers": normalized_tickers,
            "scope": scope or {},
        }
    }

    # Build conversation thread
    thread = {
        "conversation_id": conversation_id,
        "schema_version": CONVERSATION_SCHEMA_VERSION,
        "created_at": now_iso,
        "updated_at": now_iso,
        "title": first_question[:100],
        "context": {
            "tickers": normalized_tickers,
            "scope": scope or {},
            "portfolio_id": portfolio_id,
        },
        "messages": [user_message],
        "message_count": 1,
        "metadata": metadata or {},
        "source": ["copilot_conversation_service"],
    }

    # Save thread
    threads_dir = _get_conversations_dir() / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    
    saved_path = _save_conversation_thread(conversation_id, thread)
    if not saved_path:
        return {
            "status": "degraded",
            "message": "Failed to persist conversation thread",
            "conversation_id": conversation_id,
            "source": ["copilot_conversation_service", "fallback"],
        }

    # Update index - ensure directory exists
    index_dir = _get_conversations_dir()
    index_dir.mkdir(parents=True, exist_ok=True)
    
    index = _load_conversation_index()
    index_entry = {
        "conversation_id": conversation_id,
        "title": thread["title"],
        "created_at": now_iso,
        "updated_at": now_iso,
        "message_count": 1,
        "tickers": normalized_tickers,
        "portfolio_id": portfolio_id,
    }
    index["conversations"].insert(0, index_entry)
    index["count"] = len(index["conversations"])
    _save_conversation_index(index)

    return {
        "status": "created",
        "conversation_id": conversation_id,
        "created_at": now_iso,
        "title": thread["title"],
        "context": thread["context"],
        "message_count": 1,
        "store": {
            "storage_key": CONVERSATION_HISTORY_STORAGE_KEY,
            "path": str(saved_path),
            "status": "persisted",
        },
        "source": ["copilot_conversation_service"],
    }


def append_message(
    *,
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Append a message to an existing conversation.

    Args:
        conversation_id: Target conversation
        role: user or assistant
        content: Message content
        metadata: Additional metadata (verdict, confidence, tickers, etc.)

    Returns:
        Confirmation with message_id
    """
    now_iso = _utc_now_iso()

    # Load existing thread
    thread = _load_conversation_thread(conversation_id)
    if not thread:
        return {
            "status": "error",
            "message": f"Conversation {conversation_id} not found",
            "conversation_id": conversation_id,
            "source": ["copilot_conversation_service"],
        }

    # Validate role
    if role not in ("user", "assistant"):
        return {
            "status": "error",
            "message": f"Invalid role: {role}. Must be 'user' or 'assistant'",
            "source": ["copilot_conversation_service"],
        }

    # Generate message ID
    message_count = thread.get("message_count", 0)
    message_id = f"msg_{message_count + 1:03d}"

    # Build message
    message = {
        "message_id": message_id,
        "role": role,
        "content": content,
        "timestamp": now_iso,
        "metadata": metadata or {},
    }

    # Append to messages
    thread["messages"].append(message)
    thread["message_count"] = len(thread["messages"])
    thread["updated_at"] = now_iso

    # Update title if this is the first assistant response
    if role == "assistant" and message_count == 1:
        # Use first user question as title (already set)
        pass

    # Save updated thread
    saved_path = _save_conversation_thread(conversation_id, thread)
    if not saved_path:
        return {
            "status": "degraded",
            "message": "Failed to persist message",
            "conversation_id": conversation_id,
            "message_id": message_id,
            "source": ["copilot_conversation_service", "fallback"],
        }

    # Update index
    index = _load_conversation_index()
    for entry in index["conversations"]:
        if entry.get("conversation_id") == conversation_id:
            entry["updated_at"] = now_iso
            entry["message_count"] = thread["message_count"]
            break
    _save_conversation_index(index)

    return {
        "status": "appended",
        "conversation_id": conversation_id,
        "message_id": message_id,
        "role": role,
        "timestamp": now_iso,
        "message_count": thread["message_count"],
        "store": {
            "storage_key": CONVERSATION_HISTORY_STORAGE_KEY,
            "path": str(saved_path),
            "status": "persisted",
        },
        "source": ["copilot_conversation_service"],
    }


def get_conversation(
    *,
    conversation_id: str,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieve a conversation thread.

    Args:
        conversation_id: Target conversation
        limit: Max messages to return (None for all)

    Returns:
        Conversation thread with messages
    """
    thread = _load_conversation_thread(conversation_id)
    if not thread:
        return {
            "status": "not_found",
            "message": f"Conversation {conversation_id} not found",
            "conversation_id": conversation_id,
            "source": ["copilot_conversation_service"],
        }

    # Apply limit if requested
    messages = thread.get("messages", [])
    if limit and limit > 0:
        messages = messages[-limit:]

    return {
        "status": "ok",
        "conversation_id": conversation_id,
        "schema_version": thread.get("schema_version", CONVERSATION_SCHEMA_VERSION),
        "created_at": thread.get("created_at"),
        "updated_at": thread.get("updated_at"),
        "title": thread.get("title"),
        "context": thread.get("context", {}),
        "messages": messages,
        "message_count": len(messages),
        "total_message_count": thread.get("message_count", 0),
        "metadata": thread.get("metadata", {}),
        "source": ["copilot_conversation_service"],
        "freshness": _utc_now_iso(),
    }


def list_conversations(
    *,
    limit: int = 20,
    tickers: Optional[List[str]] = None,
    portfolio_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List conversation threads.

    Args:
        limit: Max conversations to return
        tickers: Filter by tickers
        portfolio_id: Filter by portfolio

    Returns:
        List of conversation summaries
    """
    index = _load_conversation_index()
    conversations = index.get("conversations", [])

    # Filter
    filtered = conversations
    if tickers:
        normalized = set(_normalize_tickers(tickers))
        filtered = [
            c for c in filtered
            if set(_normalize_tickers(c.get("tickers", []))) & normalized
        ]
    if portfolio_id:
        filtered = [
            c for c in filtered
            if c.get("portfolio_id") == portfolio_id
        ]

    # Sort by updated_at desc (already sorted)
    sorted_conversations = sorted(
        filtered,
        key=lambda c: str(c.get("updated_at", "")),
        reverse=True,
    )

    return {
        "schema_version": CONVERSATION_SCHEMA_VERSION,
        "count": index.get("count", 0),
        "filtered_count": len(filtered),
        "returned_count": len(sorted_conversations[:limit]),
        "conversations": sorted_conversations[:limit],
        "source": ["copilot_conversation_service"],
        "freshness": _utc_now_iso(),
    }


def delete_conversation(
    *,
    conversation_id: str,
) -> Dict[str, Any]:
    """
    Delete a conversation thread.

    Args:
        conversation_id: Target conversation

    Returns:
        Deletion confirmation
    """
    # Remove from index
    index = _load_conversation_index()
    original_count = index.get("count", 0)
    index["conversations"] = [
        c for c in index["conversations"]
        if c.get("conversation_id") != conversation_id
    ]
    index["count"] = len(index["conversations"])

    removed_from_index = original_count != index["count"]

    # Remove thread file
    entry_path = _conversation_entry_path(conversation_id)
    file_existed = entry_path.exists()
    try:
        if file_existed:
            entry_path.unlink()
    except Exception:
        pass

    # Save updated index
    _save_conversation_index(index)

    return {
        "status": "deleted",
        "conversation_id": conversation_id,
        "removed_from_index": removed_from_index,
        "file_existed": file_existed,
        "source": ["copilot_conversation_service"],
    }


def get_follow_up_context(
    *,
    conversation_id: str,
    max_history: int = 5,
) -> Dict[str, Any]:
    """
    Get context for follow-up question.

    Returns the last N messages to provide context for the next question.

    Args:
        conversation_id: Target conversation
        max_history: Max messages to include in context

    Returns:
        Context for follow-up (tickers, recent messages, etc.)
    """
    thread = _load_conversation_thread(conversation_id)
    if not thread:
        return {
            "status": "not_found",
            "message": f"Conversation {conversation_id} not found",
            "conversation_id": conversation_id,
            "source": ["copilot_conversation_service"],
        }

    messages = thread.get("messages", [])
    recent_messages = messages[-max_history:] if max_history > 0 else []

    # Build context summary
    context = thread.get("context", {})
    tickers = context.get("tickers", [])
    portfolio_id = context.get("portfolio_id")

    # Extract key info from recent messages
    last_user_question = None
    last_assistant_answer = None
    last_verdict = None
    last_confidence = None

    for msg in reversed(recent_messages):
        if msg.get("role") == "user" and last_user_question is None:
            last_user_question = msg.get("content")
        elif msg.get("role") == "assistant" and last_assistant_answer is None:
            last_assistant_answer = msg.get("content")
            msg_metadata = msg.get("metadata", {})
            if last_verdict is None:
                last_verdict = msg_metadata.get("verdict")
            if last_confidence is None:
                last_confidence = msg_metadata.get("confidence")

    return {
        "status": "ok",
        "conversation_id": conversation_id,
        "context": {
            "tickers": tickers,
            "portfolio_id": portfolio_id,
            "scope": context.get("scope", {}),
        },
        "recent_messages": recent_messages,
        "last_user_question": last_user_question,
        "last_assistant_answer": last_assistant_answer,
        "last_verdict": last_verdict,
        "last_confidence": last_confidence,
        "message_count": len(messages),
        "source": ["copilot_conversation_service"],
        "freshness": _utc_now_iso(),
    }


# Exports
__all__ = [
    "create_conversation",
    "append_message",
    "get_conversation",
    "list_conversations",
    "delete_conversation",
    "get_follow_up_context",
    "CONVERSATION_HISTORY_STORAGE_KEY",
    "CONVERSATION_SCHEMA_VERSION",
]
