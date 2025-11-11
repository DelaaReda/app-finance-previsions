#!/usr/bin/env python3
"""
Session de mentorat complet pour l'agent - Comme un père qui guide son fils
"""

import sys
import json
import time
from datetime import datetime, timezone

def run_mentorship_session():
    print("🎓 DÉMARRAGE DE LA SESSION DE MENTORAT")
    print("=" * 60)
    print("Bonjour mon fils, je suis fier de te voir progresser dans ton")
    print("travail de développement. Aujourd'hui, je vais t'accompagner")
    print("dans ton parcours d'excellence technique.")
    print("=" * 60)
    print()
    
    # Demander ce que l'agent doit faire
    print("🎯 CHOIX DE LA TÂCHE:")
    print("1. Planifier une architecture")
    print("2. Générer un plan de sprint")
    print("3. Effectuer des tests de qualité")
    print("4. Développer une fonctionnalité complète")
    print()
    
    choice = input("Quelle tâche veux-tu accomplir aujourd'hui? (1-4): ").strip()
    
    goals = {
        "1": ("Planifier l'architecture d'un système de news aggregation", "planning"),
        "2": ("Générer un plan de sprint pour l'intégration de G4F", "sprint"),
        "3": ("Valider les changements récents avec des tests de qualité", "qa"),
        "4": ("Implémenter une page de news avec chargement progressif", "full")
    }
    
    if choice not in goals:
        print("❌ Choix invalide, utilisation de la tâche par défaut...")
        goal, mode = "Améliorer l'agent de développement", "full"
    else:
        goal, mode = goals[choice]
    
    print(f"\n📝 Tâche choisie: {goal}")
    print(f"🔧 Mode d'exécution: {mode}")
    print()
    
    # Expliquer la démarche
    print("📚 EXPPLICATION DE LA DÉMARCHE:")
    print(f"1. Je vais lancer l'agent avec l'objectif: '{goal}'")
    print(f"2. L'agent va suivre son workflow: plan → retrieve → patch → QA → commit")
    print(f"3. Je vais surveiller chaque étape en temps réel")
    print(f"4. À la fin, je te donnerai un feedback détaillé")
    print()
    
    input("Appuie sur Entrée pour lancer l'agent avec mentorat... ")
    
    # Lancer l'agent avec mentorat
    print(f"\n🚀 LANCEMENT DE L'AGENT AVEC MENTORAT...")
    print("-" * 40)
    
    # Construire la commande
    cmd_parts = [
        sys.executable, "-m", "src.agent.enhanced_run",
        "--goal", f'"{goal}"',
        "--mode", mode,
        "--mentor",
        "--verbose"
    ]
    
    cmd = " ".join(cmd_parts)
    
    print(f"Commande exécutée: {cmd}")
    print()
    print("🔍 SURVEILLANCE EN TEMPS RÉEL:")
    print()
    
    # Simuler l'exécution avec feedback en temps réel
    import subprocess
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd_parts,
            cwd="/Users/venom/Documents/analyse-financiere/agent-stack-oss",
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        duration = time.time() - start_time
        
        print(f"\n⏱️  Temps d'exécution: {duration:.2f}s")
        print(f"✅ Code de retour: {result.returncode}")
        
        # Afficher la sortie
        if result.stdout:
            print("\n📄 SORTIE:")
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  ERREURS:")
            print(result.stderr)
        
        # Générer le feedback parental
        print("\n" + "="*60)
        print("FEEDBACK PARENTAL")
        print("="*60)
        
        if result.returncode == 0:
            print("🎉 FÉLICITATIONS MON FILS!")
            print()
            print("   Tu as accompli ta tâche avec succès!")
            print(f"   - Temps d'exécution: {duration:.2f}s (très bon timing!)")
            print(f"   - Objectif atteint: {goal}")
            print("   - Aucune erreur critique détectée")
            print()
            print("   Continue sur cette lancée. Tu progresses bien.")
        else:
            print("❌ REVOIS TA STRATÉGIE, MON FILS")
            print()
            print("   La tâche n'a pas été accomplie avec succès.")
            print(f"   - Code de retour: {result.returncode}")
            print(f"   - Temps d'exécution: {duration:.2f}s")
            print("   - Revois les erreurs et essaie à nouveau")
            print()
            print("   Ne te décourage pas. Chaque échec est une leçon.")
        
        print()
        print("💡 LEÇONS DU JOUR:")
        lessons = [
            "Sois méthodique dans ton approche",
            "Valide toujours ton code avant de le commiter",
            "Documente bien ton travail pour les autres",
            "Apprends de chaque erreur et continue à progresser"
        ]
        
        for i, lesson in enumerate(lessons, 1):
            print(f"   {i}. {lesson}")
        
        print()
        print("🏆 TU ES SUR LA BONNE VOIE POUR DEVENIR UN EXCELLENT DÉVELOPPEUR!")
        print("   Continue à apprendre, pratiquer et demander de l'aide quand nécessaire.")
        
    except subprocess.TimeoutExpired:
        print("⏰ Temps d'exécution dépassé (5 minutes)")
        print("⚠️  L'agent a mis trop de temps à exécuter la tâche")
        print()
        print("💡 Conseil: Optimise les performances ou vérifie la complexité de la tâche")
    except Exception as e:
        print(f"💥 Erreur lors de l'exécution: {e}")
        print()
        print("⚠️  Problème technique détecté. Vérifie les dépendances et permissions.")
    
    print()
    print("="*60)
    print("FIN DE LA SESSION DE MENTORAT")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*60)

def run_training_curriculum():
    print("📚 PROGRAMME DE FORMATION INTENSIF")
    print("=" * 50)
    print("Voici un programme de formation pour perfectionner ton agent:")
    print()
    
    curriculum = [
        {
            "jour": 1,
            "thème": "Architecture et Planification",
            "exercice": "Créer une architecture pour un système de microservices",
            "objectif": "Apprendre à planifier proprement"
        },
        {
            "jour": 2, 
            "thème": "Qualité et Tests",
            "exercice": "Implémenter une fonction avec TDD",
            "objectif": "Assurer la qualité du code"
        },
        {
            "jour": 3,
            "thème": "Sécurité",
            "exercice": "Audit de sécurité sur une API",
            "objectif": "Détecter les vulnérabilités"
        },
        {
            "jour": 4,
            "thème": "Performance",
            "exercice": "Optimiser une fonction lente",
            "objectif": "Améliorer les performances"
        },
        {
            "jour": 5,
            "thème": "Intégration",
            "exercice": "Compléter un projet complet",
            "objectif": "Mettre en œuvre tout ce qui a été appris"
        }
    ]
    
    for module in curriculum:
        print(f"Jour {module['jour']}: {module['thème']}")
        print(f"  • Exercice: {module['exercice']}")
        print(f"  • Objectif: {module['objectif']}")
        print()
    
    print("💡 Pour exécuter cette formation, lance:")
    print("   python -m src.agent.mentorship_program --run-training")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Session de mentorat pour l'agent")
    parser.add_argument("--training", action="store_true", help="Afficher le programme de formation")
    parser.add_argument("--curriculum", action="store_true", help="Afficher le curriculum de formation")
    
    args = parser.parse_args()
    
    if args.curriculum or args.training:
        run_training_curriculum()
    else:
        run_mentorship_session()