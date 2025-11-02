#!/usr/bin/env python3
"""
Test d'importation de toutes les pages Dash pour vérifier la migration.
"""
import sys
from pathlib import Path

# Add src to path
SRC = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SRC))

def test_imports():
    """Teste l'import de toutes les pages."""
    pages = [
        # Pages existantes
        'dashboard', 'signals', 'portfolio', 'observability', 'agents_status',
        'regimes', 'risk', 'recession', 'news', 'deep_dive', 'forecasts',
        'backtests', 'evaluation', 'quality', 'llm_judge', 'profiler', 'llm_summary',
        # Nouvelles pages migrées
        'alerts', 'watchlist', 'settings', 'memos', 'notes', 'changes',
        'events', 'earnings', 'reports', 'advisor', 'llm_models', 'home',
        # Pages integration (DEV)
        'devtools', 'integration_agent_status', 'integration_data_quality',
        'integration_macro_data', 'integration_llm_scoreboard',
    ]
    
    failed = []
    for page_name in pages:
        try:
            module = __import__(f'dash_app.pages.{page_name}', fromlist=['layout'])
            if not hasattr(module, 'layout'):
                failed.append(f"{page_name}: missing layout() function")
            else:
                print(f"✓ {page_name}")
        except Exception as e:
            failed.append(f"{page_name}: {e}")
            print(f"✗ {page_name}: {e}")
    
    if failed:
        print(f"\n❌ {len(failed)} page(s) failed:")
        for f in failed:
            print(f"  - {f}")
        return False
    else:
        print(f"\n✅ All {len(pages)} pages imported successfully!")
        return True

def test_app():
    """Teste l'import de l'app principale."""
    try:
        from dash_app.app import app, _page_registry
        pages = _page_registry()
        print(f"\n✓ App imported successfully")
        print(f"✓ {len(pages)} routes registered:")
        for route in sorted(pages.keys()):
            print(f"  - {route}")
        return True
    except Exception as e:
        print(f"\n✗ App import failed: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Testing Dash Migration - All Pages Import")
    print("=" * 60)
    print()
    
    pages_ok = test_imports()
    print()
    app_ok = test_app()
    
    print()
    print("=" * 60)
    if pages_ok and app_ok:
        print("✅ MIGRATION VALIDATION: SUCCESS")
        sys.exit(0)
    else:
        print("❌ MIGRATION VALIDATION: FAILED")
        sys.exit(1)
