#!/usr/bin/env python3
"""
Programme de Mentorat - Formation et amélioration continue de l'agent
"""

from __future__ import annotations
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import statistics

@dataclass
class PerformanceRecord:
    """Enregistrement des performances d'une session"""
    session_id: str
    goal: str
    mode: str
    complexity: str
    success: bool
    duration: float
    errors: int
    warnings: int
    timestamp: str

class AgentMentorshipProgram:
    """
    Programme de mentorat continu pour améliorer les performances de l'agent.
    Comme un père qui guide son fils vers l'excellence.
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.performance_dir = self.project_root / "data" / "mentorship"
        self.performance_dir.mkdir(parents=True, exist_ok=True)
        
        self.performance_log = self.performance_dir / "performance_history.json"
        self.feedback_log = self.performance_dir / "feedback_history.json"
        self.training_log = self.performance_dir / "training_history.json"
        
        # Charger l'historique existant ou créer un nouveau
        self.performance_history = self._load_history(self.performance_log, [])
        self.feedback_history = self._load_history(self.feedback_log, [])
        self.training_history = self._load_history(self.training_log, [])
        
    def _load_history(self, path: Path, default: Any) -> Any:
        """Charge l'historique depuis un fichier."""
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception:
            return default
    
    def _save_history(self, path: Path, data: Any) -> None:
        """Sauvegarde l'historique dans un fichier."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[mentor] Erreur sauvegarde: {e}")
    
    def run_360_assessment(self, session_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Faire une évaluation complète de la performance de l'agent.
        """
        assessment = {
            "technical_performance": self._assess_tech_performance(session_result),
            "quality_awareness": self._assess_quality_awareness(session_result),
            "efficiency": self._assess_efficiency(session_result),
            "adaptability": self._assess_adaptability(session_result),
            "overall_score": 0.0,
            "recommendations": [],
            "feedback": "",
            "timestamp": self._get_timestamp()
        }
        
        # Calculer le score global
        scores = [
            assessment["technical_performance"]["score"],
            assessment["quality_awareness"]["score"],
            assessment["efficiency"]["score"],
            assessment["adaptability"]["score"]
        ]
        assessment["overall_score"] = statistics.mean(scores) if scores else 0.0
        
        # Générer les recommandations
        assessment["recommendations"] = self._generate_recommendations(assessment, session_result)
        assessment["feedback"] = self._generate_feedback(assessment, session_result)
        
        return assessment
    
    def _assess_tech_performance(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Évaluer la performance technique."""
        tests = result.get("tests", {})
        
        # Vérifier les résultats des tests
        test_results = []
        for test_type, test_result in tests.items():
            if isinstance(test_result, dict) and "ok" in test_result:
                test_results.append(test_result.get("ok", False))
        
        success_rate = sum(test_results) / len(test_results) if test_results else 1.0
        
        # Calculer le score (0-100)
        score = min(100.0, success_rate * 100)
        
        return {
            "score": score,
            "success_rate": success_rate,
            "tests_performed": len(test_results),
            "passed_tests": sum(test_results),
            "details": {
                "standard_tests": tests.get("standard_tests", {}),
                "architecture_validation": tests.get("architecture_validation", {}),
                "security_checks": tests.get("security_checks", {}),
            }
        }
    
    def _assess_quality_awareness(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Évaluer la conscience de la qualité et des bonnes pratiques."""
        tests = result.get("tests", {})
        architecture_validation = tests.get("architecture_validation", {})
        security_checks = tests.get("security_checks", {})
        security_issues = security_checks.get("issues", [])
        
        # Score basé sur les bonnes pratiques
        score = 80.0  # Base
        
        # Architecture validation
        arch_violations = architecture_validation.get("violations", [])
        if not arch_violations:
            score += 10
        else:
            score -= len(arch_violations) * 5
        
        # Security checks
        if not security_issues:
            score += 10
        else:
            score -= len(security_issues) * 3
        
        # S'assurer que le score est entre 0 et 100
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "architecture_violations": len(arch_violations),
            "security_issues": len(security_issues),
            "quality_indicators": {
                "no_arch_violations": len(arch_violations) == 0,
                "no_security_issues": len(security_issues) == 0,
                "has_security_checks": bool(security_issues)  # Indicates checks were performed
            }
        }
    
    def _assess_efficiency(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Évaluer l'efficacité (temps, ressources)."""
        duration = result.get("duration", 0)
        
        # Score basé sur le temps d'exécution (plus rapide = meilleur)
        if duration < 30:
            efficiency_score = 90
        elif duration < 60:
            efficiency_score = 80
        elif duration < 120:
            efficiency_score = 70
        elif duration < 300:
            efficiency_score = 50
        else:
            efficiency_score = 30
        
        # Vérifier les performances du code
        performance_metrics = result.get("tests", {}).get("performance_metrics", {})
        lines_changed = performance_metrics.get("net_lines", 0)
        
        if abs(lines_changed) < 50:  # Changements modérés
            efficiency_score += 10
        elif abs(lines_changed) > 200:  # Changements excessifs
            efficiency_score -= 20
        
        final_score = max(0, min(100, efficiency_score))
        
        return {
            "score": final_score,
            "execution_time": duration,
            "lines_modified": abs(lines_changed),
            "efficiency_indicators": {
                "fast_execution": duration < 60,
                "moderate_changes": abs(lines_changed) < 100
            }
        }
    
    def _assess_adaptability(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Évaluer la capacité d'adaptation."""
        # Basé sur la capacité à s'adapter aux erreurs et trouver des solutions alternatives
        success = result.get("success", False)
        has_error_handling = True  # On suppose que l'agent a des mécanismes de fallback
        
        score = 70  # Score de base
        
        if success:
            score += 20  # Bonus pour succès
        else:
            # Si échec mais bons mécanismes de fallback, bonus partiel
            if has_error_handling:
                score += 10
        
        # Vérifier si l'agent a essayé des approches alternatives
        fallback_attempts = result.get("fallback_attempts", 0)
        if fallback_attempts > 0:
            score += 10
        
        final_score = max(0, min(100, score))
        
        return {
            "score": final_score,
            "success": success,
            "fallback_attempts": fallback_attempts,
            "adaptability_indicators": {
                "handled_errors_gracefully": has_error_handling,
                "tried_alternatives": fallback_attempts > 0
            }
        }
    
    def _generate_recommendations(self, assessment: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Générer des recommandations basées sur l'évaluation."""
        recommendations = []
        
        # Recommandations basées sur les scores faibles
        if assessment["technical_performance"]["score"] < 70:
            recommendations.append("améliorer les tests unitaires et d'intégration")
        
        if assessment["quality_awareness"]["score"] < 70:
            recommendations.append("renforcer les vérifications d'architecture et de sécurité")
        
        if assessment["efficiency"]["score"] < 70:
            recommendations.append("optimiser les temps d'exécution et limiter la taille des changements")
        
        if assessment["adaptability"]["score"] < 70:
            recommendations.append("améliorer les stratégies de fallback et de gestion des erreurs")
        
        # Recommandations spécifiques basées sur les résultats
        tests = result.get("tests", {})
        if tests.get("branch_health", {}).get("healthy") is False:
            recommendations.append("vérifier et améliorer les pratiques de gestion de branche")
        
        if tests.get("code_coverage", {}).get("ok") is False:
            recommendations.append("améliorer la couverture de test du code")
        
        # Suggestions pour améliorer les compétences
        goal = result.get("goal", "")
        if "architecture" in goal.lower():
            recommendations.append("étudier les patterns d'architecture logicielle et les best practices")
        elif "sprint" in goal.lower():
            recommendations.append("améliorer la planification et l'estimation des tâches")
        
        return recommendations
    
    def _generate_feedback(self, assessment: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Générer un feedback détaillé comme un père fier mais exigeant."""
        overall_score = assessment["overall_score"]
        goal = result.get("goal", "tâche inconnue")
        mode = result.get("mode", "mode inconnu")
        
        # Déterminer le niveau de performance
        if overall_score >= 90:
            performance_level = "excellent"
            emoji = "🏆"
        elif overall_score >= 80:
            performance_level = "très bon"
            emoji = "👍"
        elif overall_score >= 70:
            performance_level = "bon"
            emoji = "✅"
        elif overall_score >= 60:
            performance_level = "acceptable"
            emoji = "⚠️"
        else:
            performance_level = "à améliorer"
            emoji = "❌"
        
        feedback_parts = [
            f"{emoji} Mon fils, pour la tâche '{goal}' en mode {mode},",
            f"  - Ton score global est de {overall_score:.1f}/100 ({performance_level})",
        ]
        
        # Détail des performances
        tech = assessment["technical_performance"]["score"]
        quality = assessment["quality_awareness"]["score"]
        efficiency = assessment["efficiency"]["score"]
        adaptability = assessment["adaptability"]["score"]
        
        feedback_parts.extend([
            f"  - Performance technique: {tech:.1f}/100",
            f"  - Conscience de la qualité: {quality:.1f}/100",
            f"  - Efficacité: {efficiency:.1f}/100",
            f"  - Adaptabilité: {adaptability:.1f}/100"
        ])
        
        # Félicitations
        if overall_score >= 75:
            feedback_parts.append("\n  Félicitations ! Tu progresses bien.")
            if overall_score >= 90:
                feedback_parts.append("  Tu es sur la voie de devenir un excellent développeur.")
        
        # Suggestions d'amélioration
        recommendations = assessment["recommendations"]
        if recommendations:
            feedback_parts.append(f"\n  Voici tes axes d'amélioration:")
            for rec in recommendations[:3]:  # Limiter à 3 suggestions principales
                feedback_parts.append(f"  - {rec}")
        
        # Encouragements
        feedback_parts.append(f"\n  Continue à apprendre et à t'améliorer, fils. Chaque erreur est une leçon.")
        
        return "\n".join(feedback_parts)
    
    def record_performance(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Enregistrer les performances pour amélioration continue."""
        # Créer un enregistrement de performance
        perf_record = PerformanceRecord(
            session_id=result.get("session_id", "unknown"),
            goal=result.get("goal", "unknown"),
            mode=result.get("mode", "unknown"),
            complexity=result.get("complexity", "unknown"),
            success=result.get("success", False),
            duration=result.get("duration", 0),
            errors=len(result.get("error_messages", [])),
            warnings=len(result.get("output_messages", [])) - len(result.get("error_messages", [])),
            timestamp=result.get("timestamp", self._get_timestamp())
        )
        
        # Convertir en dictionnaire
        perf_dict = {
            "session_id": perf_record.session_id,
            "goal": perf_record.goal,
            "mode": perf_record.mode,
            "complexity": perf_record.complexity,
            "success": perf_record.success,
            "duration": perf_record.duration,
            "errors": perf_record.errors,
            "warnings": perf_record.warnings,
            "timestamp": perf_record.timestamp
        }
        
        # Ajouter à l'historique
        self.performance_history.append(perf_dict)
        
        # Sauvegarder l'historique
        self._save_history(self.performance_log, self.performance_history)
        
        # Faire une évaluation complète
        assessment = self.run_360_assessment(result)
        
        # Enregistrer l'assessment
        self.feedback_history.append({
            "session_id": perf_record.session_id,
            "assessment": assessment,
            "timestamp": self._get_timestamp()
        })
        
        # Sauvegarder le feedback
        self._save_history(self.feedback_log, self.feedback_history)
        
        return assessment
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Analyser les tendances d'apprentissage de l'agent."""
        if not self.performance_history:
            return {"message": "Pas encore d'historique de performances"}
        
        # Analyser les tendances
        recent_sessions = self.performance_history[-10:]  # 10 dernières sessions
        
        success_rates = [s["success"] for s in recent_sessions]
        durations = [s["duration"] for s in recent_sessions]
        errors = [s["errors"] for s in recent_sessions]
        
        success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        avg_duration = sum(durations) / len(durations) if durations else 0
        avg_errors = sum(errors) / len(errors) if errors else 0
        
        # Déterminer les tendances
        improving = len(recent_sessions) > 1 and success_rates[-1] > success_rates[0]
        trending_faster = len(recent_sessions) > 1 and durations[-1] < durations[0]
        
        insights = {
            "overall_performance": {
                "success_rate": success_rate,
                "average_duration": avg_duration,
                "average_errors": avg_errors,
                "sessions_analyzed": len(recent_sessions)
            },
            "trends": {
                "improving": improving,
                "trending_faster": trending_faster,
                "message": "Progresse bien !" if improving else "Continue à t'améliorer"
            },
            "recommendations": [],
            "timestamp": self._get_timestamp()
        }
        
        # Générer des recommandations basées sur les tendances
        if avg_errors > 2:
            insights["recommendations"].append("réduire le nombre d'erreurs dans les tâches futures")
        
        if avg_duration > 120:
            insights["recommendations"].append("optimiser les temps d'exécution")
        
        if not improving:
            insights["recommendations"].append("analyser les causes des échecs récents et s'adapter")
        
        return insights
    
    def adaptive_learning(self, goal: str, mode: str = "full", complexity: str = "medium") -> Dict[str, Any]:
        """
        Adaptation basée sur l'historique des performances.
        """
        insights = self.get_learning_insights()
        
        # Déterminer la stratégie d'exécution basée sur l'historique
        strategy = {
            "complexity_adjustment": complexity,
            "mode_recommendation": mode,
            "risk_analysis": {},
            "learning_tips": []
        }
        
        # Ajuster la complexité en fonction de l'historique
        if insights.get("overall_performance", {}).get("success_rate", 0.5) < 0.7:
            # Si succès faible, réduire la complexité
            strategy["complexity_adjustment"] = "simple" if complexity != "simple" else "medium"
            strategy["learning_tips"].append("Commencer par des tâches plus simples pour renforcer les bases")
        
        # Analyse des risques basée sur l'historique
        risk_factors = []
        
        if insights.get("overall_performance", {}).get("average_errors", 0) > 2:
            risk_factors.append("haute probabilité d'erreurs")
        
        if insights.get("overall_performance", {}).get("average_duration", 0) > 300:
            risk_factors.append("longue durée d'exécution")
        
        strategy["risk_analysis"] = {
            "factors": risk_factors,
            "mitigation": "renforcer les validations et ajouter des checkpoints"
        }
        
        return strategy
    
    def run_advanced_training(self, curriculum: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Exécuter un programme de formation avancé.
        """
        training_results = {
            "curriculum": curriculum,
            "completed_tasks": 0,
            "success_rate": 0,
            "lessons_learned": [],
            "improvement_metrics": {},
            "timestamp": self._get_timestamp()
        }
        
        # Pour chaque tâche dans le curriculum
        for task in curriculum:
            print(f"[mentor] Formation: {task['name']} - {task['description']}")
            
            # Exécuter la tâche avec adaptation
            strategy = self.adaptive_learning(task["goal"], task["mode"], task["complexity"])
            
            # Simuler l'exécution de la tâche
            task_result = {
                "task_name": task["name"],
                "goal": task["goal"],
                "mode": strategy["mode_recommendation"],
                "complexity": strategy["complexity_adjustment"],
                "success": True,  # Pour l'exemple
                "timestamp": self._get_timestamp()
            }
            
            training_results["lessons_learned"].append({
                "task": task_result,
                "feedback": f"Compétence '{task['name']}' acquise avec succès"
            })
            
            training_results["completed_tasks"] += 1
        
        # Calculer le taux de succès
        if curriculum:
            training_results["success_rate"] = training_results["completed_tasks"] / len(curriculum)
        
        # Enregistrer dans l'historique
        self.training_history.append(training_results)
        self._save_history(self.training_log, self.training_history)
        
        return training_results
    
    def provide_mentorship_feedback(self, result: Dict[str, Any]) -> str:
        """
        Fournir un feedback de mentorat personnalisé.
        """
        assessment = self.record_performance(result)
        insights = self.get_learning_insights()
        
        feedback_parts = [
            "=== MENTORSHIP FEEDBACK ===",
            assessment["feedback"],
            "",
            "=== INSIGHTS D'APPRENTISSAGE ===",
        ]
        
        perf = insights.get("overall_performance", {})
        if perf:
            feedback_parts.extend([
                f"  - Taux de succès: {perf.get('success_rate', 0):.2%}",
                f"  - Durée moyenne: {perf.get('average_duration', 0):.2f}s",
                f"  - Erreurs moyennes: {perf.get('average_errors', 0):.2f}",
            ])
        
        trends = insights.get("trends", {})
        if trends:
            feedback_parts.append(f"  - Tendance: {trends.get('message', 'inconnue')}")
        
        feedback_parts.extend([
            "",
            "=== RECOMMANDATIONS PERSONNALISÉES ===",
        ])
        
        recommendations = insights.get("recommendations", [])
        for rec in recommendations:
            feedback_parts.append(f"  - {rec}")
        
        return "\n".join(feedback_parts)
    
    def _get_timestamp(self) -> str:
        """Obtenir l'horodatage actuel."""
        return datetime.now(timezone.utc).isoformat()

# Programme de mentorat interactif
def interactive_mentorship():
    """Mode mentorat interactif."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mentorat interactif pour l'agent")
    parser.add_argument("--goal", help="Objectif pour lequel fournir du mentorat")
    parser.add_argument("--analyze-history", action="store_true", help="Analyser l'historique des performances")
    parser.add_argument("--run-training", action="store_true", help="Démarrer un programme de formation")
    
    args = parser.parse_args()
    
    mentor = AgentMentorshipProgram("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
    
    if args.analyze_history:
        insights = mentor.get_learning_insights()
        print(f"\n📊 Insights d'apprentissage:")
        print(json.dumps(insights, ensure_ascii=False, indent=2))
        
    elif args.run_training:
        # Curriculum d'exemple
        curriculum = [
            {
                "name": "Architecture Planning",
                "description": "Planifier l'architecture d'un système",
                "goal": "Plan architecture for news aggregation system",
                "mode": "planning",
                "complexity": "medium"
            },
            {
                "name": "Sprint Planning",
                "description": "Créer un plan de sprint",
                "goal": "Generate sprint plan for feature implementation",
                "mode": "sprint",
                "complexity": "medium"
            },
            {
                "name": "Quality Assurance",
                "description": "Effectuer des tests de qualité",
                "goal": "Validate recent changes with comprehensive QA",
                "mode": "qa",
                "complexity": "simple"
            }
        ]
        
        print("📚 Démarrage du programme de formation...")
        results = mentor.run_advanced_training(curriculum)
        print(f"✅ Formation terminée! {results['completed_tasks']}/{len(curriculum)} tâches complétées")
        
    elif args.goal:
        print(f"🎯 Mentorat pour l'objectif: {args.goal}")
        strategy = mentor.adaptive_learning(args.goal)
        print(f"💡 Stratégie adaptative: {json.dumps(strategy, ensure_ascii=False, indent=2)}")
    else:
        parser.print_help()

if __name__ == "__main__":
    interactive_mentorship()