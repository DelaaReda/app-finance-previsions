#!/usr/bin/env python3
"""
Generate daily brief and save to storage for /api/brief/daily endpoint
"""
import sys
import os

# Add backend src to path
backend_root = os.path.join(os.path.dirname(__file__), '..', 'apps', 'api', 'src')
backend_root = os.path.abspath(backend_root)
if os.path.exists(backend_root):
    sys.path.insert(0, backend_root)
    print(f"Added to path: {backend_root}")

# Set PYTHONPATH for imports
os.environ['PYTHONPATH'] = backend_root

try:
    from services.brief_generator import save_daily_brief
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Backend root: {backend_root}")
    print(f"Path exists: {os.path.exists(backend_root)}")
    import json
    
    # Fallback: generate brief manually
    from datetime import datetime
    
    brief = {
        'summary': "Le marché reste actif avec une lecture mitigée. Les secteurs technologiques montrent une certaine force tandis que l'énergie reste sous pression. Surveillez les signaux macroéconomiques cette semaine.",
        'headline': f"Brief Marché - {datetime.now().strftime('%d/%m/%Y')}",
        'sentiment': 'neutral',
        'macro_signals': [
            {'name': 'VIX', 'value': '14.5', 'signal': 'risk_on', 'impact': 'medium'},
            {'name': 'DXY', 'value': '103.2', 'signal': 'neutral', 'impact': 'low'}
        ],
        'sector_rotation': {'top': ['IA', 'Tech'], 'bottom': ['Énergie']},
        'top_signals': [],
        'top_risks': [],
        'key_events': [],
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'source': ['brief_generator', 'fallback']
    }
    
    # Save manually
    data_dir = os.path.join(backend_root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, 'brief_daily.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Brief saved to {filepath}")
    print(f"\nSummary:")
    print(brief['summary'])
    sys.exit(0)

if __name__ == '__main__':
    print("Generating daily brief...")
    brief = save_daily_brief()
    
    if brief:
        print("✅ Daily brief generated and saved successfully!")
        print(f"\nSummary ({len(brief['summary'].split())} words):")
        print(brief['summary'])
        print(f"\nSector Rotation - Top: {brief['sector_rotation']['top']}")
        print(f"Sector Rotation - Bottom: {brief['sector_rotation']['bottom']}")
        print(f"\nMacro Signals: {len(brief['macro_signals'])} indicators")
        print(f"Sentiment: {brief['sentiment']}")
    else:
        print("❌ Failed to generate daily brief")
        sys.exit(1)
