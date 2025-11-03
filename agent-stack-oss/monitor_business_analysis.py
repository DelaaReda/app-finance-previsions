#!/usr/bin/env python3
"""
Script to monitor the progress of the business analysis task
"""

import time
import json
from pathlib import Path

def monitor_progress():
    """Monitor the progress of the business analysis task"""
    monitoring_dir = Path("data/monitoring")
    
    print("🔍 Surveillance de la tâche d'analyse business en cours...")
    print("=" * 60)
    
    # Wait a bit for the task to start generating logs
    time.sleep(10)
    
    start_time = time.time()
    max_wait_time = 300  # 5 minutes maximum
    
    while time.time() - start_time < max_wait_time:
        # Check for new metrics files
        if monitoring_dir.exists():
            metrics_files = list(monitoring_dir.glob("*.json"))
            if metrics_files:
                # Get the most recent metrics file
                latest = max(metrics_files, key=lambda f: f.stat().st_mtime)
                
                try:
                    with open(latest, 'r') as f:
                        metrics = json.load(f)
                    
                    print(f"📊 Session: {metrics.get('session_id', 'N/A')}")
                    print(f"⏱️  Durée: {metrics.get('duration', 0):.2f}s")
                    print(f"✅ Terminée: {'Oui' if metrics.get('completed_successfully', False) else 'Non'}")
                    print(f"📌 Objectif: {metrics.get('goal', 'N/A')[:50]}...")
                    
                    # Show nodes executed
                    nodes = metrics.get('nodes_executed', [])
                    if nodes:
                        print(f"🔧 Nœuds exécutés: {', '.join(nodes)}")
                    
                    print("-" * 60)
                    
                    # If completed, show the result
                    if metrics.get('completed_successfully', False):
                        print("🎉 Tâche terminée avec succès!")
                        return
                        
                except Exception as e:
                    print(f"❌ Erreur de lecture des métriques: {e}")
        
        # Check event logs
        events_file = monitoring_dir / "events.jsonl"
        if events_file.exists():
            try:
                # Read the last few lines of events
                with open(events_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        print("📜 Événements récents:")
                        for line in lines[-3:]:  # Last 3 events
                            event = json.loads(line.strip())
                            print(f"   • {event.get('message', 'N/A')}")
                        print()
            except Exception as e:
                print(f"❌ Erreur de lecture des événements: {e}")
        
        time.sleep(15)  # Check every 15 seconds
    
    print("⏰ Temps d'attente dépassé. La tâche continue peut-être en arrière-plan.")

if __name__ == "__main__":
    monitor_progress()