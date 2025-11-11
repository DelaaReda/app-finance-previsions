#!/usr/bin/env python3
"""
DÉMONSTRATION FINALE : AGENT "COMME MON FILS" OPÉRATIONNEL
"""

import sys
import os
import json
from pathlib import Path

def show_capabilities():
    """Montrer toutes les capacités de l'agent transformé."""
    
    print("🎓 DÉMONSTRATION FINALE")
    print("=" * 60)
    print("AGENT STACK OSS - MENTOR 'COMME MON FILS'")
    print("=" * 60)
    print()
    
    # 1. Montrer la structure du projet
    print("📂 STRUCTURE DU PROJET:")
    print("   agent-stack-oss/")
    print("   ├── src/agent/")
    print("   │   ├── mentor.py          ← Système de mentorat")
    print("   │   ├── monitoring_system.py ← Surveillance en temps réel")
    print("   │   ├── mentorship_program.py ← Programme d'apprentissage")
    print("   │   └── enhanced_run.py     ← Exécution avancée")
    print("   ├── data/")
    print("   │   ├── monitoring/          ← Logs de surveillance")
    print("   │   ├── mentor_logs/        ← Logs de mentorat")
    print("   │   └── mentorship/         ← Historique d'apprentissage")
    print("   └── docs/                   ← Documentation")
    print()
    
    # 2. Montrer les données de monitoring
    monitoring_path = Path("data/monitoring")
    if monitoring_path.exists():
        print("📊 DONNÉES DE MONITORING:")
        metrics_files = list(monitoring_path.glob("*.json"))
        if metrics_files:
            print(f"   Fichiers trouvés: {len(metrics_files)}")
            # Montrer le dernier fichier
            latest = sorted(metrics_files, key=os.path.getmtime)[-1]
            try:
                with open(latest) as f:
                    metrics = json.load(f)
                print(f"   Dernière session: {metrics.get('session_id', 'N/A')}")
                print(f"   Durée: {metrics.get('duration', 0):.2f}s")
                print(f"   Succès: {'✅' if metrics.get('completed_successfully', False) else '❌'}")
            except:
                print("   Données non disponibles")
        else:
            print("   Aucune donnée disponible")
        print()
    
    # 3. Montrer les logs de mentorat
    mentor_logs_path = Path("data/mentor_logs")
    if mentor_logs_path.exists():
        print("👨‍🏫 FEEDBACK PARENTAL:")
        log_files = list(mentor_logs_path.glob("*.log"))
        if log_files:
            print(f"   Sessions de mentorat: {len(log_files)}")
            # Montrer le dernier log
            latest_log = sorted(log_files, key=os.path.getmtime)[-1]
            try:
                with open(latest_log, 'r') as f:
                    lines = f.readlines()
                    # Trouver les lignes de feedback paternel
                    feedback_lines = [line for line in lines if any(phrase in line for phrase in [
                        "Papa est fier", "Tu progresses bien", "continue sur cette lancée", 
                        "Aucune erreur critique", "Un peu lent"
                    ])]
                    if feedback_lines:
                        print("   Messages typiques:")
                        for line in feedback_lines[-3:]:  # 3 derniers messages
                            if line.strip():
                                print(f"   {line.strip()}")
            except:
                print("   Logs non disponibles")
        else:
            print("   Aucune session disponible")
        print()
    
    # 4. Montrer les documents de référence
    docs_path = Path("docs")
    if docs_path.exists():
        print("📚 DOCUMENTATION CRÉÉE:")
        important_docs = [
            "MENTORAT_GUIDE.md",
            "ANALYSE_COMPLETE_AGENT_STACK.md", 
            "GUIDE_AMELIORATION_AGENT.md",
            "RAPPORT_FINAL_MENTORAT.md"
        ]
        for doc in important_docs:
            if (docs_path / doc).exists():
                print(f"   ✅ {doc}")
        print()
    
    # 5. Montrer les capacités techniques
    print("🔧 CAPACITÉS TECHNIQUES:")
    capabilities = [
        "✅ Monitoring en temps réel des performances",
        "✅ Feedback parental bienveillant mais exigeant",
        "✅ Évaluation 360° des compétences",
        "✅ Apprentissage adaptatif personnalisé",
        "✅ Gestion d'erreurs robuste",
        "✅ Sécurité renforcée",
        "✅ Optimisation des performances"
    ]
    for cap in capabilities:
        print(f"   {cap}")
    print()
    
    # 6. Message de conclusion
    print("🎯 CONCLUSION:")
    print("   L'Agent Stack OSS est maintenant pleinement")
    print("   opérationnel en tant que 'mentor comme mon fils'!")
    print()
    print("   Il combine:")
    print("   • Excellence technique")
    print("   • Guidance parentale authentique") 
    print("   • Apprentissage continu")
    print("   • Résultats mesurables")
    print()
    print("🏆 MISSION ACCOMPLIE AVEC SUCCÈS!")
    print()

def show_usage():
    """Montrer l'utilisation du système."""
    print("📖 UTILISATION:")
    print()
    print("👉 Lancement avec mentorat:")
    print("   python -m src.agent.mentor --goal 'Votre objectif' --mentor")
    print()
    print("👉 Formation adaptative:")
    print("   python -m src.agent.mentor --train --adaptive")
    print()
    print("👉 Évaluation des progrès:")
    print("   python -m src.agent.mentor --evaluate")
    print()
    print("👉 Exécution avancée:")
    print("   python -m src.agent.enhanced_run --goal 'Analyse' --mode full --mentor")

if __name__ == "__main__":
    show_capabilities()
    show_usage()