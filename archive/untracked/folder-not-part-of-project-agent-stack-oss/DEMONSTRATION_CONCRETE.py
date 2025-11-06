#!/usr/bin/env python3
"""
DÉMONSTRATION CONCRÈTE DES CAPACITÉS DE L'AGENT STACK OSS
======================================================

Cette démonstration montre ce que l'Agent Stack OSS peut réellement livrer
en situation réelle, comme un père qui observe son fils travailler.
"""

import sys
import os
import json
import time
from pathlib import Path

def run_agent_task_demonstration():
    """Démonstration concrète des capacités de l'agent."""
    
    print("🎓 DÉMONSTRATION CONCRÈTE DE L'AGENT STACK OSS")
    print("=" * 60)
    print()
    print("👨 [Papa] Bonjour mon fils, aujourd'hui je vais t'observer")
    print("           travailler pour voir ce que tu sais faire.")
    print()
    print("🤖 [Agent] Bonjour Papa, je suis prêt à montrer mes capacités!")
    print()
    
    # Tâche concrète : Analyse de la structure du projet parent
    task = "Analyse la structure de base du projet d'analyse financière situé dans le dossier parent"
    
    print(f"📝 TÂCHE ASSIGNÉE: {task}")
    print()
    print("👨 [Papa] Vas-y, montre-moi ce que tu sais faire!")
    print()
    
    # Exécuter la tâche avec l'agent
    start_time = time.time()
    
    try:
        # Importer les composants de l'agent
        sys.path.insert(0, '.')
        from src.agent.graph import build_graph
        from src.agent.config import AgentConfig
        
        print("🔍 [Agent] Initialisation en cours...")
        
        # Construire le graph
        graph = build_graph()
        print("✅ [Agent] Graph construit avec succès")
        
        # Préparer l'état initial
        state = {
            "goal": task,
            "plan": {},
            "context_docs": [],
            "patch": {},
            "tests": {},
            "result": {},
            "session_id": "demo_" + str(int(time.time())),
            "start_time": time.time(),
        }
        
        print("🚀 [Agent] Démarrage de l'analyse...")
        
        # Exécuter le workflow
        result_state = graph.invoke(state)
        
        execution_time = time.time() - start_time
        
        print("✅ [Agent] Analyse terminée!")
        print(f"⏱️  [Agent] Temps d'exécution: {execution_time:.2f}s")
        print()
        
        # Montrer les résultats
        print("📊 [Agent] RÉSULTATS DE L'ANALYSE:")
        print("-" * 40)
        
        # Analyser le résultat
        result = result_state.get("result", {})
        if result:
            print("✅ [Agent] Résultat final:")
            for key, value in result.items():
                if key not in ["duration", "session_id"]:
                    print(f"   • {key}: {value}")
        
        # Montrer le plan créé
        plan = result_state.get("plan", {})
        if plan:
            print()
            print("📝 [Agent] Plan d'action élaboré:")
            steps = plan.get("steps", [])
            files = plan.get("files", [])
            if steps:
                print("   Étapes:")
                for i, step in enumerate(steps[:5], 1):  # Max 5 étapes
                    print(f"   {i}. {step}")
            if files:
                print("   Fichiers ciblés:")
                for file in files[:3]:  # Max 3 fichiers
                    print(f"   • {file}")
        
        # Feedback paternel
        print()
        print("👨 [Papa] Très bon travail, fils!")
        if execution_time < 30:
            print("⚡ [Papa] Excelle en rapidité!")
        elif execution_time < 60:
            print("✅ [Papa] Bonne performance!")
        else:
            print("🐢 [Papa] Un peu lent, mais la qualité d'abord!")
        
        success_rate = result.get("success_rate", 0) if isinstance(result, dict) else 0
        if success_rate > 0.8:
            print("🏆 [Papa] Taux de succès excellent!")
        elif success_rate > 0.6:
            print("👍 [Papa] Bon taux de succès, continue!")
        else:
            print("💡 [Papa] Peux mieux faire, revois ton approche.")
            
        print()
        print("💪 [Papa] Tu progresses bien, continue comme ça!")
        print("📚 [Papa] N'oublie pas: chaque erreur est une leçon.")
        
    except Exception as e:
        error_time = time.time() - start_time
        print(f"❌ [Agent] Erreur rencontrée après {error_time:.2f}s")
        print(f"   Détails: {str(e)}")
        print()
        print("👨 [Papa] Papa, Papa... Ce n'est pas grave, fils.")
        print("💡 [Papa] C'est une leçon pour progresser.")
        print("🔧 [Papa] Revois l'erreur et essaie à nouveau.")
        
        # Montrer plus de détails sur l'erreur
        import traceback
        print()
        print("📋 Traceback détaillé:")
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("🎯 DÉMONSTRATION TERMINÉE")
    print("=" * 60)

def show_agent_capabilities_summary():
    """Montrer un résumé des capacités de l'agent."""
    print()
    print("📊 CAPACITÉS ACTUELLES DE L'AGENT")
    print("=" * 40)
    
    capabilities = {
        "Architecture": [
            "✅ LangGraph pour orchestration",
            "✅ Nœuds spécialisés (plan, retrieve, patch, qa, commit)",
            "✅ Gestion d'état typée"
        ],
        "Techniques": [
            "✅ Intégration LLM (g4f, OpenAI, Ollama)",
            "✅ Outils Git (patch, commit, branch)",
            "✅ RAG (Retrieval Augmented Generation)",
            "✅ CI/CD (tests, linting, build)"
        ],
        "Monitoring": [
            "✅ Suivi en temps réel des performances", 
            "✅ Journalisation détaillée",
            "✅ Système de mentorat intégré"
        ],
        "Sécurité": [
            "✅ Validation des entrées",
            "✅ Branch protection",
            "✅ Safe file operations"
        ]
    }
    
    for category, items in capabilities.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  {item}")
    
    print()
    print("🎯 POTENTIEL À DÉVELOPPER")
    print("-" * 30)
    print("  • Analyse de qualité de code approfondie")
    print("  • Évaluation de sécurité avancée") 
    print("  • Optimisation des performances")
    print("  • Feedback mentorat personnalisé")
    print("  • Apprentissage adaptatif")

if __name__ == "__main__":
    run_agent_task_demonstration()
    show_agent_capabilities_summary()