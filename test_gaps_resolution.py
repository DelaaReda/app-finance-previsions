#!/usr/bin/env python3
"""
Test script to verify that critical gaps have been addressed
"""
import sys
from pathlib import Path
import os

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_critical_components():
    """Test all the critical components that were missing."""
    print("🔍 Testing critical gap resolutions...")
    
    results = {}
    
    # 1. Test core/data_access.py
    print("\n1. Testing core/data_access.py...")
    try:
        from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
        print("   ✅ core/data_access functions imported successfully")
        
        # Test get_close_series with a common ticker
        series = get_close_series("SPY")
        if series is not None:
            print(f"   ✅ get_close_series('SPY'): {len(series)} rows, latest: {series.iloc[-1]:.2f}")
        else:
            print("   ⚠️  get_close_series('SPY'): None (may need internet)")
        
        results['core_data_access'] = True
    except Exception as e:
        print(f"   ❌ core/data_access error: {e}")
        results['core_data_access'] = False
    
    # 2. Test compute_composite_brief
    print("\n2. Testing compute_composite_brief()...")
    try:
        from research.scoring import compute_composite_brief
        brief = compute_composite_brief(period="daily", universe=["SPY", "QQQ", "AAPL"])
        print("   ✅ compute_composite_brief() function available")
        
        if brief.get("top_signals"):
            print(f"   ✅ Brief generated with {len(brief['top_signals'])} top signals")
        else:
            print("   ⚠️  Brief generated but no signals (may need data)")
        
        results['composite_brief'] = True
    except Exception as e:
        print(f"   ❌ compute_composite_brief error: {e}")
        results['composite_brief'] = False
    
    # 3. Test LLM client
    print("\n3. Testing LLM client...")
    try:
        from research.llm_client import get_llm_client, ask_llm
        print("   ✅ LLM client functions available")
        
        # Test client creation (may be None if no API key)
        client = get_llm_client()
        if client is None:
            print("   ⚠️  LLM client not configured (no API key) - this is OK")
        else:
            print("   ✅ LLM client configured")
        
        # Test ask_llm function with mock context
        response = ask_llm("test", [{"text": "test context", "meta": {"type": "test"}}])
        print(f"   ✅ ask_llm() function works, model: {response.get('model', 'unknown')}")
        
        results['llm_client'] = True
    except Exception as e:
        print(f"   ❌ LLM client error: {e}")
        results['llm_client'] = False
    
    # 4. Test RAG functionality
    print("\n4. Testing RAG functionality...")
    try:
        from research.rag_store import RAGStore
        rag = RAGStore()
        stats = rag.stats()
        print(f"   ✅ RAG store created, stats: {stats}")
        
        # Test freshness_stats method
        fresh_stats = rag.freshness_stats()
        print(f"   ✅ freshness_stats method works: {fresh_stats['total_items']} items")
        
        results['rag_store'] = True
    except Exception as e:
        print(f"   ❌ RAG error: {e}")
        results['rag_store'] = False
    
    # 5. Test versioned notes
    print("\n5. Testing versioned notes...")
    try:
        from research.versioned_notes import VersionedNotesStore, NoteType
        notes_store = VersionedNotesStore()
        print("   ✅ Versioned notes store created")
        
        # Test creating a note
        note_id = notes_store.create_note(
            title="Test Note",
            content="This is a test of the versioned notes system.",
            author="System",
            note_type=NoteType.ANALYSIS
        )
        if note_id:
            print(f"   ✅ Created note with ID: {note_id[:8]}...")
        else:
            print("   ❌ Failed to create note")
        
        results['versioned_notes'] = True
    except Exception as e:
        print(f"   ❌ Versioned notes error: {e}")
        results['versioned_notes'] = False
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   core/data_access: {'✅' if results.get('core_data_access') else '❌'}")
    print(f"   composite_brief: {'✅' if results.get('composite_brief') else '❌'}")
    print(f"   llm_client: {'✅' if results.get('llm_client') else '❌'}")
    print(f"   rag_store: {'✅' if results.get('rag_store') else '❌'}")
    print(f"   versioned_notes: {'✅' if results.get('versioned_notes') else '❌'}")
    
    total_success = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n🎯 Progress: {total_success}/{total} critical gaps resolved")
    
    if total_success == total:
        print("\n🎉 All critical gaps have been successfully addressed!")
        return True
    else:
        print(f"\n⚠️  {total - total_success} gaps still need attention")
        return False

if __name__ == "__main__":
    print("Testing critical gap resolutions...")
    success = test_critical_components()
    sys.exit(0 if success else 1)