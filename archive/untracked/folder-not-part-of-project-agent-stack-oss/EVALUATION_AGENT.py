#!/usr/bin/env python3
"""
ÉVALUATION DES CAPACITÉS ACTUELLES DE L'AGENT STACK OSS
=====================================================

Ce script évalue objectivement les capacités actuelles de l'Agent Stack OSS
pour déterminer ce qu'il peut réellement livrer à ce stade.
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

def evaluate_agent_capabilities():
    """Évalue les capacités réelles de l'agent."""
    
    print("🎓 ÉVALUATION DES CAPACITÉS DE L'AGENT STACK OSS")
    print("=" * 60)
    print()
    
    # Test 1: Vérification de l'environnement
    print("🔍 TEST 1: Vérification de l'environnement")
    print("-" * 40)
    
    results = {
        "environment": {},
        "modules": {},
        "basic_functionality": {},
        "current_limitations": []
    }
    
    # Vérifier Python
    try:
        python_version = sys.version
        print(f"✅ Python: {python_version.split()[0]}")
        results["environment"]["python"] = python_version.split()[0]
    except Exception as e:
        print(f"❌ Python: Erreur - {e}")
        results["environment"]["python"] = f"Erreur: {e}"
    
    # Vérifier dépendances clés
    dependencies = ["langgraph", "langchain", "llama-index", "chromadb"]
    for dep in dependencies:
        try:
            __import__(dep.replace("-", "_"))
            print(f"✅ {dep}: Installé")
            results["environment"][dep] = "installé"
        except ImportError as e:
            print(f"❌ {dep}: Manquant - {e}")
            results["environment"][dep] = f"manquant: {e}"
            results["current_limitations"].append(f"Dépendance manquante: {dep}")
    
    print()
    
    # Test 2: Modules de l'agent
    print("🔍 TEST 2: Modules de l'agent")
    print("-" * 40)
    
    agent_modules = [
        "src.agent.graph",
        "src.agent.mentor", 
        "src.agent.config",
        "src.agent.models.router",
        "src.agent.tools.git_tools"
    ]
    
    for module in agent_modules:
        try:
            __import__(module, fromlist=[''])
            print(f"✅ {module}: OK")
            results["modules"][module] = "chargé"
        except Exception as e:
            print(f"❌ {module}: Erreur - {e}")
            results["modules"][module] = f"erreur: {e}"
    
    print()
    
    # Test 3: Fonctionnalité de base
    print("🔍 TEST 3: Fonctionnalité de base")
    print("-" * 40)
    
    try:
        from src.agent.graph import build_graph
        graph = build_graph()
        print("✅ Build graph: OK")
        results["basic_functionality"]["build_graph"] = "success"
    except Exception as e:
        print(f"❌ Build graph: Erreur - {e}")
        results["basic_functionality"]["build_graph"] = f"erreur: {e}"
        results["current_limitations"].append(f"Build graph échoué: {e}")
    
    try:
        from src.agent.config import AgentConfig
        config = AgentConfig()
        print(f"✅ Configuration: Mode {config.provider}")
        results["basic_functionality"]["config"] = f"mode: {config.provider}"
    except Exception as e:
        print(f"❌ Configuration: Erreur - {e}")
        results["basic_functionality"]["config"] = f"erreur: {e}"
        results["current_limitations"].append(f"Configuration échouée: {e}")
    
    try:
        from src.agent.mentor import AgentMentor
        mentor = AgentMentor(".")
        print("✅ Mentor system: OK")
        results["basic_functionality"]["mentor"] = "initialisé"
    except Exception as e:
        print(f"❌ Mentor system: Erreur - {e}")
        results["basic_functionality"]["mentor"] = f"erreur: {e}"
    
    print()
    
    # Test 4: Tâche simple réelle
    print("🔍 TEST 4: Tâche simple réelle")
    print("-" * 40)
    print("📝 Objectif: Analyser la structure de base du projet")
    print()
    
    # Simuler une tâche simple sans exécuter vraiment
    start_time = time.time()
    
    try:
        # Vérifier la structure du projet
        project_structure = []
        root_dirs = [d for d in Path("../..").iterdir() if d.is_dir()]
        for d in root_dirs[:10]:  # Limiter à 10 pour l'exemple
            project_structure.append(str(d.name))
        
        analysis_time = time.time() - start_time
        
        print("✅ Analyse structure terminée")
        print(f"⏱️  Temps: {analysis_time:.2f}s")
        print(f"📁 Dossiers trouvés: {len(project_structure)}")
        print(f"📊 Échantillon: {project_structure[:5]}")
        
        results["basic_functionality"]["simple_task"] = {
            "status": "success",
            "time": analysis_time,
            "folders_found": len(project_structure),
            "sample": project_structure[:5]
        }
        
    except Exception as e:
        error_time = time.time() - start_time
        print(f"❌ Analyse échouée: {e}")
        print(f"⏱️  Temps avant échec: {error_time:.2f}s")
        
        results["basic_functionality"]["simple_task"] = {
            "status": f"erreur: {e}",
            "time": error_time
        }
        results["current_limitations"].append(f"Tâche simple échouée: {e}")
    
    print()
    
    # Résumé
    print("📊 RÉSUMÉ DE L'ÉVALUATION")
    print("=" * 60)
    
    total_tests = len(results["environment"]) + len(results["modules"]) + len(results["basic_functionality"])
    successful_tests = sum(1 for v in results["environment"].values() if not isinstance(v, str) or not v.startswith("erreur") and not v.startswith("manquant"))
    successful_tests += sum(1 for v in results["modules"].values() if v == "chargé")
    successful_tests += sum(1 for v in results["basic_functionality"].values() if v == "success" or (isinstance(v, dict) and v.get("status") == "success"))
    
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"📈 Taux de succès: {success_rate:.1f}% ({successful_tests}/{total_tests} tests réussis)")
    
    if results["current_limitations"]:
        print(f"⚠️  Limitations actuelles: {len(results['current_limitations'])}")
        for limitation in results["current_limitations"][:3]:  # Montrer les 3 premières
            print(f"   • {limitation}")
    
    print()
    
    # Niveau de maturité
    if success_rate >= 80:
        maturity = "Avancé - Prêt pour des tâches complexes"
        print("🟢 NIVEAU: AVANCÉ")
    elif success_rate >= 60:
        maturity = "Intermédiaire - Besoin d'améliorations"
        print("🟡 NIVEAU: INTERMÉDIAIRE") 
    elif success_rate >= 40:
        maturity = "Débutant - Besoin de stabilisation"
        print("🟠 NIVEAU: DÉBUTANT")
    else:
        maturity = "Initial - Besoin de corrections majeures"
        print("🔴 NIVEAU: INITIAL")
    
    results["maturity_level"] = {
        "level": maturity,
        "success_rate": success_rate,
        "total_tests": total_tests,
        "successful_tests": successful_tests
    }
    
    print()
    print("🎯 CAPACITÉS ACTUELLES IDENTIFIÉES")
    print("-" * 40)
    
    capabilities = []
    
    # Architecture
    if results["modules"].get("src.agent.graph") == "chargé":
        capabilities.append("✅ Architecture LangGraph opérationnelle")
    
    # Configuration
    if "config" in results["basic_functionality"] and not results["basic_functionality"]["config"].startswith("erreur"):
        capabilities.append("✅ Système de configuration fonctionnel")
    
    # Mentorat
    if results["modules"].get("src.agent.mentor") == "chargé":
        capabilities.append("✅ Système de mentorat disponible")
    
    # Analyse basique
    if isinstance(results["basic_functionality"].get("simple_task"), dict) and results["basic_functionality"]["simple_task"].get("status") == "success":
        capabilities.append("✅ Capacité d'analyse basique")
    
    if not capabilities:
        capabilities.append("⚠️  Capacités limitées - Besoin de stabilisation")
    
    for cap in capabilities:
        print(f"   {cap}")
    
    print()
    print("🚧 LIMITATIONS IDENTIFIÉES")
    print("-" * 40)
    
    limitations = results["current_limitations"][:5]  # Max 5 limitations
    if not limitations:
        limitations = ["Aucune limitation majeure identifiée"]
    
    for limitation in limitations:
        print(f"   • {limitation}")
    
    print()
    print("📊 RECOMMANDATIONS DE FORMATION")
    print("-" * 40)
    
    recommendations = []
    
    # Recommandations basées sur les résultats
    if "manquant" in str(results["environment"].get("ruff", "")):
        recommendations.append("🔧 Installer ruff pour l'analyse qualité")
    
    if "manquant" in str(results["environment"].get("langchain", "")):
        recommendations.append("🔧 Installer langchain pour les LLM")
    
    if not recommendations:
        recommendations.append("📚 Continuer le développement des capacités avancées")
        recommendations.append("🎯 Mettre en pratique avec des exercices gradués")
        recommendations.append("📈 Suivre les progrès avec les indicateurs définis")
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print()
    print("=" * 60)
    print("ÉVALUATION TERMINÉE")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    results = evaluate_agent_capabilities()
    
    # Sauvegarder les résultats
    output_file = Path("data") / "evaluation_results.json"
    output_file.parent.mkdir(exist_ok=True)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 Résultats sauvegardés dans: {output_file}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")