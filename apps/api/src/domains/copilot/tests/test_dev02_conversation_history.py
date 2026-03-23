"""
BATCH-73-DEV-02: Conversation History + Follow-up Questions - Delivery Proof Tests

Tests for:
- Conversation creation
- Message append (user + assistant)
- Conversation retrieval
- Follow-up context injection
- Conversation listing
- Integration with /api/copilot/ask endpoint
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.copilot.api import copilot as copilot_route
from domains.copilot.application import conversation_history


# Test fixtures
_test_dir: Path | None = None


def _setup_test_dir() -> Path:
    """Create isolated test directory."""
    global _test_dir
    if _test_dir is None:
        _test_dir = Path(__file__).parent / ".test_conversations"
        _test_dir.mkdir(parents=True, exist_ok=True)
    return _test_dir


def _cleanup_test_dir():
    """Clean up test directory."""
    global _test_dir
    if _test_dir and _test_dir.exists():
        shutil.rmtree(_test_dir, ignore_errors=True)
        _test_dir = None


def _client() -> TestClient:
    """Create test client."""
    app = FastAPI()
    app.include_router(copilot_route.router, prefix="/api")
    return TestClient(app)


def setup_function():
    """Setup before each test."""
    test_dir = _setup_test_dir()
    os.environ["COPILOT_CONVERSATIONS_DIR"] = str(test_dir)
    # Clear cache in conversation_history module
    conversation_history._conversations_dir_cache = None


def teardown_function():
    """Teardown after each test."""
    _cleanup_test_dir()
    if "COPILOT_CONVERSATIONS_DIR" in os.environ:
        del os.environ["COPILOT_CONVERSATIONS_DIR"]


# ============================================================================
# Conversation History Service Tests
# ============================================================================


def test_create_conversation_basic():
    """Test basic conversation creation."""
    result = conversation_history.create_conversation(
        first_question="What's moving the market today?",
        tickers=["AAPL", "MSFT"],
    )
    
    assert result["status"] == "created"
    assert "conversation_id" in result
    assert len(result["conversation_id"]) == 16
    assert result["title"] == "What's moving the market today?"
    assert result["message_count"] == 1
    assert result["context"]["tickers"] == ["AAPL", "MSFT"]
    assert "store" in result
    assert result["store"]["status"] == "persisted"


def test_create_conversation_with_portfolio():
    """Test conversation creation with portfolio context."""
    result = conversation_history.create_conversation(
        first_question="How does my portfolio look today?",
        portfolio_id="portfolio-123",
        scope={"portfolio_id": "portfolio-123"},
    )
    
    assert result["status"] == "created"
    assert result["context"]["portfolio_id"] == "portfolio-123"
    assert result["context"]["scope"]["portfolio_id"] == "portfolio-123"


def test_append_message_user():
    """Test appending user message."""
    conv_result = conversation_history.create_conversation(
        first_question="Should I buy NVDA?",
        tickers=["NVDA"],
    )
    conv_id = conv_result["conversation_id"]
    
    result = conversation_history.append_message(
        conversation_id=conv_id,
        role="user",
        content="What about earnings risk?",
        metadata={"follow_up": True},
    )
    
    assert result["status"] == "appended"
    assert result["role"] == "user"
    assert result["message_count"] == 2
    assert "message_id" in result


def test_append_message_assistant():
    """Test appending assistant message."""
    conv_result = conversation_history.create_conversation(
        first_question="Should I buy NVDA?",
        tickers=["NVDA"],
    )
    conv_id = conv_result["conversation_id"]
    
    result = conversation_history.append_message(
        conversation_id=conv_id,
        role="assistant",
        content="Buy NVDA with 1w horizon. Momentum is strong.",
        metadata={
            "verdict": "buy",
            "confidence": 0.75,
            "horizon": "1w",
        },
    )
    
    assert result["status"] == "appended"
    assert result["role"] == "assistant"
    assert result["message_count"] == 2
    assert result["message_id"] == "msg_002"


def test_get_conversation():
    """Test retrieving conversation."""
    conv_result = conversation_history.create_conversation(
        first_question="Market outlook?",
        tickers=["SPY"],
    )
    conv_id = conv_result["conversation_id"]
    
    # Add assistant response
    conversation_history.append_message(
        conversation_id=conv_id,
        role="assistant",
        content="Neutral stance. Wait for CPI.",
        metadata={"verdict": "hold"},
    )
    
    result = conversation_history.get_conversation(conversation_id=conv_id)
    
    assert result["status"] == "ok"
    assert result["conversation_id"] == conv_id
    assert result["message_count"] == 2
    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "user"
    assert result["messages"][1]["role"] == "assistant"
    assert result["messages"][1]["metadata"]["verdict"] == "hold"


def test_get_conversation_with_limit():
    """Test retrieving conversation with message limit."""
    conv_result = conversation_history.create_conversation(
        first_question="Multi-turn conversation",
    )
    conv_id = conv_result["conversation_id"]
    
    # Add multiple messages
    for i in range(5):
        conversation_history.append_message(
            conversation_id=conv_id,
            role="assistant" if i % 2 == 0 else "user",
            content=f"Message {i+2}",
        )
    
    result = conversation_history.get_conversation(conversation_id=conv_id, limit=3)
    
    assert result["status"] == "ok"
    assert result["returned_count"] == 3
    assert result["total_message_count"] == 6  # 1 initial + 5 added


def test_list_conversations():
    """Test listing conversations."""
    # Create multiple conversations
    conv_ids = []
    for i in range(3):
        result = conversation_history.create_conversation(
            first_question=f"Question {i}",
            tickers=["AAPL"] if i == 0 else ["MSFT"] if i == 1 else None,
        )
        conv_ids.append(result["conversation_id"])
    
    result = conversation_history.list_conversations(limit=10)
    
    assert result["status"] is None or "ok" not in result or result.get("returned_count", 0) >= 3
    assert result["returned_count"] >= 3


def test_list_conversations_filter_by_tickers():
    """Test filtering conversations by tickers."""
    conv_result = conversation_history.create_conversation(
        first_question="AAPL question",
        tickers=["AAPL"],
    )
    conv_id = conv_result["conversation_id"]
    
    result = conversation_history.list_conversations(tickers=["AAPL"], limit=10)
    
    assert result["returned_count"] >= 1
    conv_ids = [c["conversation_id"] for c in result["conversations"]]
    assert conv_id in conv_ids


def test_get_follow_up_context():
    """Test getting follow-up context."""
    conv_result = conversation_history.create_conversation(
        first_question="Should I buy NVDA?",
        tickers=["NVDA"],
        portfolio_id="portfolio-123",
    )
    conv_id = conv_result["conversation_id"]
    
    # Add assistant response
    conversation_history.append_message(
        conversation_id=conv_id,
        role="assistant",
        content="Buy NVDA. Strong momentum.",
        metadata={
            "verdict": "buy",
            "confidence": 0.8,
            "horizon": "1w",
        },
    )
    
    result = conversation_history.get_follow_up_context(
        conversation_id=conv_id,
        max_history=5,
    )
    
    assert result["status"] == "ok"
    assert result["context"]["tickers"] == ["NVDA"]
    assert result["context"]["portfolio_id"] == "portfolio-123"
    assert result["last_verdict"] == "buy"
    assert result["last_confidence"] == 0.8
    assert len(result["recent_messages"]) == 2


def test_delete_conversation():
    """Test deleting conversation."""
    conv_result = conversation_history.create_conversation(
        first_question="Temporary question",
    )
    conv_id = conv_result["conversation_id"]
    
    result = conversation_history.delete_conversation(conversation_id=conv_id)
    
    assert result["status"] == "deleted"
    assert result["removed_from_index"] is True
    
    # Verify deletion
    get_result = conversation_history.get_conversation(conversation_id=conv_id)
    assert get_result["status"] == "not_found"


def test_append_message_invalid_role():
    """Test appending message with invalid role."""
    conv_result = conversation_history.create_conversation(
        first_question="Test",
    )
    conv_id = conv_result["conversation_id"]
    
    result = conversation_history.append_message(
        conversation_id=conv_id,
        role="system",  # Invalid
        content="Test",
    )
    
    assert result["status"] == "error"
    assert "Invalid role" in result["message"]


def test_get_nonexistent_conversation():
    """Test retrieving nonexistent conversation."""
    result = conversation_history.get_conversation(
        conversation_id="nonexistent123456",
    )
    
    assert result["status"] == "not_found"


# ============================================================================
# API Endpoint Tests
# ============================================================================


def test_copilot_conversation_create_endpoint():
    """Test /api/copilot/conversation/create endpoint."""
    client = _client()
    
    response = client.post(
        "/api/copilot/conversation/create",
        json={
            "first_question": "What's the outlook for tech stocks?",
            "tickers": ["AAPL", "MSFT", "GOOGL"],
        },
    )
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "created"
    assert "conversation_id" in payload["data"]


def test_copilot_conversation_get_endpoint():
    """Test /api/copilot/conversation/{id} endpoint."""
    client = _client()
    
    # Create conversation
    create_response = client.post(
        "/api/copilot/conversation/create",
        json={"first_question": "Test question"},
    )
    conv_id = create_response.json()["data"]["conversation_id"]
    
    # Get conversation
    response = client.get(f"/api/copilot/conversation/{conv_id}")
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["conversation_id"] == conv_id


def test_copilot_conversations_list_endpoint():
    """Test /api/copilot/conversations endpoint."""
    client = _client()
    
    # Create a conversation
    client.post(
        "/api/copilot/conversation/create",
        json={"first_question": "Test"},
    )
    
    response = client.get("/api/copilot/conversations")
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "conversations" in payload["data"]
    assert payload["data"]["returned_count"] >= 1


def test_copilot_ask_with_conversation_id():
    """Test /api/copilot/ask with conversation_id for follow-up."""
    client = _client()
    
    # Create conversation
    create_response = client.post(
        "/api/copilot/conversation/create",
        json={
            "first_question": "Should I buy NVDA?",
            "tickers": ["NVDA"],
        },
    )
    conv_id = create_response.json()["data"]["conversation_id"]
    
    # Ask follow-up question with conversation_id
    response = client.post(
        "/api/copilot/ask",
        json={
            "question": "What about earnings risk?",
            "conversation_id": conv_id,
        },
    )
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    
    # Verify conversation metadata in response
    data = payload["data"]
    assert "conversation" in data
    assert data["conversation"]["conversation_id"] == conv_id
    assert "message_id" in data["conversation"]
    assert "message_count" in data["conversation"]
    
    # Verify follow-up context
    assert "follow_up_context" in data
    assert data["follow_up_context"]["conversation_id"] == conv_id


def test_copilot_ask_follow_up_inherits_tickers():
    """Test that follow-up questions inherit tickers from conversation context."""
    client = _client()
    
    # Create conversation with specific tickers
    create_response = client.post(
        "/api/copilot/conversation/create",
        json={
            "first_question": "Tech outlook?",
            "tickers": ["AAPL", "MSFT"],
        },
    )
    conv_id = create_response.json()["data"]["conversation_id"]
    
    # Ask follow-up without explicit tickers
    response = client.post(
        "/api/copilot/ask",
        json={
            "question": "Should I be worried about the upcoming event?",
            "conversation_id": conv_id,
        },
    )
    
    assert response.status_code == 200
    payload = response.json()
    
    # Verify tickers were inherited
    data = payload["data"]
    assert "follow_up_context" in data
    assert data["follow_up_context"]["tickers"] == ["AAPL", "MSFT"]


def test_copilot_conversation_followup_context_endpoint():
    """Test /api/copilot/conversation/{id}/followup endpoint."""
    client = _client()
    
    # Create conversation
    create_response = client.post(
        "/api/copilot/conversation/create",
        json={
            "first_question": "Market outlook?",
            "tickers": ["SPY", "QQQ"],
            "portfolio_id": "portfolio-456",
        },
    )
    conv_id = create_response.json()["data"]["conversation_id"]
    
    # Add assistant response
    client.post(
        "/api/copilot/ask",
        json={
            "question": "Market outlook?",
            "conversation_id": conv_id,
        },
    )
    
    # Get follow-up context
    response = client.get(f"/api/copilot/conversation/{conv_id}/followup")
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["context"]["tickers"] == ["SPY", "QQQ"]
    assert payload["data"]["context"]["portfolio_id"] == "portfolio-456"


def test_copilot_conversation_delete_endpoint():
    """Test /api/copilot/conversation/{id} DELETE endpoint."""
    client = _client()
    
    # Create conversation
    create_response = client.post(
        "/api/copilot/conversation/create",
        json={"first_question": "Temporary"},
    )
    conv_id = create_response.json()["data"]["conversation_id"]
    
    # Delete
    response = client.delete(f"/api/copilot/conversation/{conv_id}")
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "deleted"


def test_personal_finance_conversation_endpoints():
    """Test /api/personal-finance/conversation/* alias endpoints."""
    client = _client()
    
    # Create via personal-finance namespace
    response = client.post(
        "/api/personal-finance/conversation/create",
        json={
            "first_question": "Portfolio advice?",
            "portfolio_id": "my-portfolio",
        },
    )
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "conversation_id" in payload["data"]
    
    conv_id = payload["data"]["conversation_id"]
    
    # Get via personal-finance namespace
    response = client.get(f"/api/personal-finance/conversation/{conv_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    
    # List via personal-finance namespace
    response = client.get("/api/personal-finance/conversations")
    assert response.status_code == 200
    assert response.json()["ok"] is True


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_conversation_flow():
    """Test complete conversation flow: create -> ask -> follow-up -> retrieve."""
    client = _client()
    
    # Step 1: Create conversation
    create_response = client.post(
        "/api/copilot/conversation/create",
        json={
            "first_question": "Should I invest in NVDA now?",
            "tickers": ["NVDA"],
        },
    )
    assert create_response.status_code == 200
    conv_id = create_response.json()["data"]["conversation_id"]
    
    # Step 2: First ask (via conversation creation, message already logged)
    # Let's also call ask to get a full response
    ask1_response = client.post(
        "/api/copilot/ask",
        json={
            "question": "Should I invest in NVDA now?",
            "conversation_id": conv_id,
            "tickers": ["NVDA"],
        },
    )
    assert ask1_response.status_code == 200
    assert ask1_response.json()["data"]["conversation"]["message_count"] >= 2
    
    # Step 3: Follow-up question
    ask2_response = client.post(
        "/api/copilot/ask",
        json={
            "question": "What's the main risk?",
            "conversation_id": conv_id,
        },
    )
    assert ask2_response.status_code == 200
    assert ask2_response.json()["data"]["conversation"]["message_count"] >= 4
    
    # Verify follow-up context was used
    assert "follow_up_context" in ask2_response.json()["data"]
    
    # Step 4: Retrieve full conversation
    get_response = client.get(f"/api/copilot/conversation/{conv_id}")
    assert get_response.status_code == 200
    conv_data = get_response.json()["data"]
    assert conv_data["message_count"] >= 4
    assert len(conv_data["messages"]) >= 4
    
    # Verify message structure
    user_msgs = [m for m in conv_data["messages"] if m["role"] == "user"]
    assistant_msgs = [m for m in conv_data["messages"] if m["role"] == "assistant"]
    assert len(user_msgs) >= 2
    assert len(assistant_msgs) >= 2


def test_conversation_persistence():
    """Test that conversations persist across service calls."""
    # Create conversation
    result = conversation_history.create_conversation(
        first_question="Persistent question",
        tickers=["AAPL"],
    )
    conv_id = result["conversation_id"]
    
    # Add message
    conversation_history.append_message(
        conversation_id=conv_id,
        role="assistant",
        content="Persistent answer",
        metadata={"verdict": "hold"},
    )
    
    # Retrieve (should load from disk)
    result = conversation_history.get_conversation(conversation_id=conv_id)
    
    assert result["status"] == "ok"
    assert result["messages"][1]["content"] == "Persistent answer"
    assert result["messages"][1]["metadata"]["verdict"] == "hold"
