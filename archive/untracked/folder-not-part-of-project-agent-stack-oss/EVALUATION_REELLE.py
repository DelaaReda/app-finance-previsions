#!/usr/bin/env python3
"""
ÉVALUATION RÉELLE DES CAPACITÉS DE L'AGENT STACK OSS
===============================================

Évaluation réaliste de ce que l'Agent Stack OSS peut livrer aujourd'hui,
comme un père qui teste les vraies capacités de son fils.
"""

import sys
import os
import json
import time
from pathlib import Path

def evaluate_actual_agent_capabilities():
    """Évaluer les vraies capacités de l'agent."""
    
    print("🎓 ÉVALUATION RÉELLE DES CAPACITÉS DE L'AGENT STACK OSS")
    print("=" * 60)
    print()
    print("👨 [Papa] Bon, fils, aujourd'hui je vais vraiment tester")
    print("           ce que tu sais faire, sans tricher.")
    print()
    print("🤖 [Agent] Papa, je suis prêt! Montre-moi ce que tu veux.")
    print()
    
    # Test 1: Vérifier ce que l'agent peut faire réellement
    print("🔍 TEST 1: Capacités techniques de base")
    print("-" * 45)
    
    capabilities = {
        "core_modules": [],
        "available_tools": [],
        "llm_integration": None,
        "workflow_nodes": []
    }
    
    # Vérifier les modules de base
    core_modules = [
        "src.agent.graph",
        "src.agent.config", 
        "src.agent.mentor",
        "src.agent.models.router"
    ]
    
    for module in core_modules:
        try:
            __import__(module, fromlist=[''])
            print(f"✅ {module}")
            capabilities["core_modules"].append(module)
        except Exception as e:
            print(f"❌ {module} - {str(e)[:50]}...")
    
    print()
    
    # Vérifier les outils disponibles
    print("🔧 TEST 2: Outils disponibles")
    print("-" * 30)
    
    tools = [
        "src.agent.tools.git_tools",
        "src.agent.tools.ci_tools", 
        "src.agent.tools.rag_tools",
        "src.agent.tools.fs_tools"
    ]
    
    for tool_module in tools:
        try:
            __import__(tool_module, fromlist=[''])
            print(f"✅ {tool_module}")
            capabilities["available_tools"].append(tool_module)
        except Exception as e:
            print(f"❌ {tool_module} - {str(e)[:50]}...")
    
    print()
    
    # Vérifier l'intégration LLM
    print("🤖 TEST 3: Intégration LLM")
    print("-" * 25)
    
    try:
        from src.agent.models.router import get_llm
        llm = get_llm("test")
        print(f"✅ LLM Router: Configuré (provider: {type(llm).__name__})")
        capabilities["llm_integration"] = type(llm).__name__
    except Exception as e:
        print(f"❌ LLM Router: Erreur - {str(e)[:50]}...")
        capabilities["llm_integration"] = f"erreur: {str(e)[:50]}"
    
    print()
    
    # Vérifier les nœuds du workflow
    print("🔄 TEST 4: Nœuds du workflow")
    print("-" * 30)
    
    try:
        from src.agent.graph import build_graph
        graph = build_graph()
        
        # Essayer de compiler le graph pour voir les nœuds
        compiled_graph = graph.compile()
        print("✅ Graph compilation: OK")
        
        # Vérifier les nœuds disponibles
        nodes = ["plan", "retrieve", "patch", "qa", "commit"]
        for node in nodes:
            try:
                # Vérifier si le nœud existe
                if hasattr(graph, '_nodes') and node in graph._nodes:
                    print(f"✅ Nœud {node}: Disponible")
                    capabilities["workflow_nodes"].append(node)
                else:
                    print(f"⚠️  Nœud {node}: À vérifier")
            except:
                print(f"❓ Nœud {node}: Statut inconnu")
                
    except Exception as e:
        print(f"❌ Graph: Erreur - {str(e)[:50]}...")
    
    print()
    
    # Test 5: Configuration actuelle
    print("⚙️  TEST 5: Configuration actuelle")
    print("-" * 30)
    
    try:
        from src.agent.config import AgentConfig
        config = AgentConfig()
        print(f"✅ Provider LLM: {config.provider}")
        print(f"✅ Modèle: {config.model}")
        print(f"✅ Mode direct write: {config.allow_direct_write}")
        
        # Vérifier les chemins autorisés
        if config.safe_paths:
            print(f"✅ Chemins sécurisés: {len(config.safe_paths)} configurés")
        
    except Exception as e:
        print(f"❌ Configuration: Erreur - {str(e)[:50]}...")
    
    print()
    
    # Analyse des capacités réelles
    print("📊 ANALYSE DES CAPACITÉS RÉELLES")
    print("=" * 45)
    
    # Calculer le score de maturité
    core_modules_count = len(capabilities["core_modules"])
    tools_count = len(capabilities["available_tools"]) 
    workflow_nodes_count = len(capabilities["workflow_nodes"])
    
    total_possible = len(core_modules) + len(tools) + 1 + len(["plan", "retrieve", "patch", "qa", "commit"])
    total_achieved = core_modules_count + tools_count + (1 if capabilities["llm_integration"] and not capabilities["llm_integration"].startswith("erreur") else 0) + workflow_nodes_count
    
    maturity_score = (total_achieved / total_possible) * 100 if total_possible > 0 else 0
    
    print(f"📈 Score de maturité: {maturity_score:.1f}% ({total_achieved}/{total_possible})")
    
    # Niveau selon le score
    if maturity_score >= 80:
        level = "AVANCÉ - Prêt pour des tâches complexes"
        emoji = "🟢"
    elif maturity_score >= 60:
        level = "INTERMÉDIAIRE - Besoin d'améliorations ciblées"
        emoji = "🟡"
    elif maturity_score >= 40:
        level = "DÉBUTANT - Besoin de stabilisation"
        emoji = "🟠"
    else:
        level = "INITIAL - Besoin de corrections majeures"
        emoji = "🔴"
    
    print(f"{emoji} Niveau: {level}")
    
    print()
    print("🎯 CE QUE L'AGENT PEUT LIVRER AUJOURD'HUI")
    print("-" * 50)
    
    # Ce qui fonctionne
    working_features = []
    
    if core_modules_count >= 3:
        working_features.append("✅ Architecture de base opérationnelle")
    
    if tools_count >= 3:
        working_features.append("✅ Outils techniques disponibles")
    
    if capabilities["llm_integration"] and not capabilities["llm_integration"].startswith("erreur"):
        working_features.append("✅ Intégration LLM fonctionnelle")
    
    if workflow_nodes_count >= 3:
        working_features.append("✅ Workflow d'exécution partiel")
    
    if not working_features:
        working_features.append("⚠️  Fonctionnalités limitées - Besoin de stabilisation")
        working_features.append("💡 Commencer par les bases (graph, config, tools)")
    
    for feature in working_features:
        print(f"   {feature}")
    
    print()
    print("🚧 LIMITATIONS ACTUELLES")
    print("-" * 30)
    
    limitations = []
    
    # Identifier les problèmes spécifiques
    if "src.agent.tools.git_tools" not in capabilities["available_tools"]:
        limitations.append("❌ Outils Git non disponibles")
    
    if "src.agent.tools.rag_tools" not in capabilities["available_tools"]:
        limitations.append("❌ Outils RAG non disponibles")
    
    # Vérifier s'il y a des erreurs dans l'intégration
    if capabilities["llm_integration"] and "erreur" in capabilities["llm_integration"]:
        limitations.append("❌ Problèmes d'intégration LLM")
    
    if not limitations:
        limitations.append("⚠️  Quelques erreurs mineures à corriger")
        limitations.append("💡 Problèmes d'exécution complète du workflow")
    
    for limitation in limitations[:3]:  # Max 3 limitations
        print(f"   {limitation}")
    
    print()
    print("🎯 LIVRABLES POSSIBLES ACTUELLEMENT")
    print("-" * 40)
    
    possible_deliverables = []
    
    if "src.agent.graph" in capabilities["core_modules"]:
        possible_deliverables.append("📄 Analyse structurelle de projets")
        possible_deliverables.append("📋 Plans d'action basiques")
    
    if "src.agent.tools.rag_tools" in capabilities["available_tools"]:
        possible_deliverables.append("📚 Synthèses documentaires")
        possible_deliverables.append("🔍 Recherches contextuelles")
    
    if "src.agent.tools.fs_tools" in capabilities["available_tools"]:
        possible_deliverables.append("📝 Documentation technique")
        possible_deliverables.append("📊 Rapports d'analyse")
    
    if not possible_deliverables:
        possible_deliverables.append("⚠️  Livrables limités - Stabiliser d'abord")
        possible_deliverables.append("💡 Commencer par les capacités de base")
    
    for deliverable in possible_deliverables[:6]:  # Max 6 livrables
        print(f"   {deliverable}")
    
    print()
    print("👨 CONSEILS DE PAPA POUR PROGRESSER")
    print("-" * 40)
    
    advice = [
        "🔧 Corriger les dépendances manquantes (ruff, pylint)",
        "📚 Améliorer la documentation des modules",
        "🧪 Développer des tests unitaires pour chaque nœud",
        "📊 Mettre en place monitoring avancé des performances",
        "🎯 Commencer par des tâches simples et progressives"
    ]
    
    for tip in advice:
        print(f"   {tip}")
    
    print()
    print("📈 PLAN D'AMÉLIORATION PROGRESSIF")
    print("-" * 40)
    
    improvement_plan = [
        "Semaine 1: Stabiliser les dépendances et l'environnement",
        "Semaine 2: Corriger l'intégration LLM et les outils",
        "Semaine 3: Optimiser le workflow et les nœuds",
        "Semaine 4: Mettre en place tests et monitoring avancé"
    ]
    
    for week in improvement_plan:
        print(f"   📅 {week}")
    
    print()
    print("=" * 60)
    print("🎯 ÉVALUATION TERMINÉE - CAPACITÉS RÉELLES IDENTIFIÉES")
    print("=" * 60)
    
    return {
        "capabilities": capabilities,
        "maturity_score": maturity_score,
        "level": level,
        "working_features": working_features,
        "limitations": limitations,
        "possible_deliverables": possible_deliverables
    }

if __name__ == "__main__":
    results = evaluate_actual_agent_capabilities()
    
    # Sauvegarder les résultats
    try:
        output_file = Path("data") / "real_capabilities_evaluation.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"💾 Résultats sauvegardés dans: {output_file}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")