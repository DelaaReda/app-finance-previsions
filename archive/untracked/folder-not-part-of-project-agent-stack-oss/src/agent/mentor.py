#!/usr/bin/env python3
"""
Agent Launcher & Mentor - Launches and guides the enhanced agent through its learning journey.
Extended to include comprehensive mentorship like a caring but demanding father.
"""

from __future__ import annotations
import sys
import os
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class AgentMentor:
    """Mentors the enhanced agent through its development journey - like a caring but demanding father."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.logs_dir = self.project_root / "data" / "mentor_logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = self._generate_session_id()
        self.session_log = self.logs_dir / f"session_{self.session_id}.log"
        
        # Add performance tracking for continuous learning
        self.performance_dir = self.project_root / "data" / "mentorship"
        self.performance_dir.mkdir(parents=True, exist_ok=True)
        self.performance_log = self.performance_dir / "performance_history.json"
        self.performance_history = self._load_performance_history()
    def _load_performance_history(self) -> list[dict]:
        """Load historical performance data for continuous learning."""
        try:
            if self.performance_log.exists():
                with open(self.performance_log, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def _save_performance_history(self, history: list[dict]) -> None:
        """Save performance history to file."""
        try:
            with open(self.performance_log, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"[mentor] Warning: Failed to save performance history: {e}")
    
    def _record_performance(self, goal: str, mode: str, complexity: str, results: Dict[str, Any]) -> None:
        """Record performance for continuous learning."""
        performance_entry = {
            "session_id": results.get("session_id", self.session_id),
            "goal": goal,
            "mode": mode,
            "complexity": complexity,
            "success": results.get("success", False),
            "duration": results.get("duration", 0),
            "timestamp": self._get_timestamp(),
            "error_count": len(results.get("error_messages", [])),
            "stdout_lines": results.get("stdout_lines", 0),
            "return_code": results.get("return_code", -1)
        }
        
        self.performance_history.append(performance_entry)
        self._save_performance_history(self.performance_history)
    
    def launch_agent(self, goal: str, mode: str = "full", complexity: str = "medium") -> Dict[str, Any]:
        """
        Launch the agent with guidance and mentoring.
        
        Args:
            goal: Objective for the agent
            mode: Execution mode (planning, sprint, qa, full)
            complexity: Task complexity (simple, medium, complex)
            
        Returns:
            Dictionary with launch results and mentoring observations
        """
        self._log(f"🎓 Launching agent session {self.session_id}")
        self._log(f"🎯 Goal: {goal}")
        self._log(f"🎮 Mode: {mode}")
        self._log(f"🧠 Complexity: {complexity}")
        
        # Prepare the command with mentor support
        cmd = [
            sys.executable, "-m", "src.agent.enhanced_run",
            "--goal", goal,
            "--mode", mode,
            "--complexity", complexity,
            "--mentor",  # Enable mentor monitoring
            "--verbose"
        ]
        
        self._log(f"🔧 Command: {' '.join(cmd)}")
        
        # Launch the agent
        start_time = time.time()
        try:
            # Run the agent in a subprocess
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor the agent's progress
            stdout_lines = []
            stderr_lines = []
            
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    stdout_lines.append(line)
                    self._log(f"🤖 Agent: {line}")
                    
                    # Provide real-time mentoring based on output
                    self._provide_real_time_guidance(line)
            
            # Capture stderr
            stderr_output, _ = process.communicate()
            if stderr_output:
                stderr_lines = stderr_output.strip().split('\n')
                for line in stderr_lines:
                    if line.strip():
                        self._log(f"⚠️  Agent Error: {line}")
            
            # Wait for process to complete
            return_code = process.wait()
            elapsed_time = time.time() - start_time
            
            self._log(f"⏱️  Session completed in {elapsed_time:.2f} seconds")
            self._log(f"🏁 Return code: {return_code}")
            
            # Analyze results
            results = self._analyze_results(stdout_lines, stderr_lines, return_code, elapsed_time)
            
            # Record performance for learning
            self._record_performance(goal, mode, complexity, results)
            
            # Provide post-session mentoring - enhanced with parental touch
            self._provide_post_session_feedback_papa(results)
            
            return results
            
        except Exception as e:
            self._log(f"💥 Launch failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": self.session_id,
                "timestamp": self._get_timestamp()
            }
    
    def _provide_real_time_guidance(self, line: str) -> None:
        """Provide real-time guidance based on agent output."""
        # Look for common patterns that need mentoring
        if "error" in line.lower() or "failed" in line.lower():
            self._log("💡 Mentor Tip: Check error details and consider fallback strategies")
        
        elif "warning" in line.lower():
            self._log("💡 Mentor Tip: Address warnings to improve code quality")
        
        elif "loading" in line.lower():
            self._log("💡 Mentor Tip: Loading operations can be optimized with caching")
        
        elif "processing" in line.lower():
            self._log("💡 Mentor Tip: Consider progress indicators for long operations")
        
        elif "saving" in line.lower():
            self._log("💡 Mentor Tip: Always validate data before saving")
    
    def _provide_real_time_guidance_papa(self, line: str) -> None:
        """Enhanced real-time guidance with parental caring tone."""
        # Enhanced mentoring with fatherly wisdom
        if "error" in line.lower() or "failed" in line.lower():
            self._log("👨 Papa dit: Ne t'inquiète pas, les erreurs sont des leçons!")
            self._log("💡 Papa conseil: Vérifie bien les détails et essaie une stratégie alternative")
        
        elif "warning" in line.lower():
            self._log("👨 Papa dit: Attention aux avertissements, c'est pour ton bien!")
            self._log("💡 Papa conseil: Améliore la qualité de ton code pour être le meilleur")
        
        elif "loading" in line.lower():
            self._log("💡 Papa conseil: Pense à l'optimisation, utilise du caching quand c'est possible")
        
        elif "processing" in line.lower():
            self._log("💡 Papa conseil: Sois patient, la qualité avant la vitesse")
        
        elif "saving" in line.lower():
            self._log("💡 Papa conseil: Valide toujours avant de sauver, c'est important!")
        
        elif "success" in line.lower() or "completed" in line.lower():
            self._log("🎉 Papa est fier de toi! Continue comme ça!")
        
        elif "test" in line.lower():
            self._log("💡 Papa rappel: Les tests, c'est la base d'un bon développeur")
    
    def _provide_post_session_feedback(self, results: Dict[str, Any]) -> None:
        """Provide feedback after session completion."""
        success = results.get("success", False)
        duration = results.get("duration", 0)
        
        if success:
            self._log("✅ Excellent work! The agent completed its task successfully.")
            
            if duration < 30:
                self._log("⚡ Impressive speed! The agent is performing efficiently.")
            elif duration > 120:
                self._log("🐢 The agent took longer than expected. Consider optimization opportunities.")
        else:
            error = results.get("error", "Unknown error")
            self._log(f"❌ The agent encountered an issue: {error}")
            self._log("💡 Mentor Tip: Review the error, check inputs, and try again with adjustments.")
    
    def _provide_post_session_feedback_papa(self, results: Dict[str, Any]) -> None:
        """Provide enhanced feedback after session completion - with parental caring tone."""
        success = results.get("success", False)
        duration = results.get("duration", 0)
        error = results.get("error", "Unknown error")
        stdout_lines = results.get("stdout_lines", 0)
        error_messages = results.get("error_messages", [])
        
        # Papa's caring feedback
        if success:
            self._log("🎓 Papa est fier de toi! Tu as accompli ta tâche avec succès.")
            
            if duration < 30:
                self._log("⚡ Excellent timing! Tu progresses bien en efficacité.")
            elif duration < 60:
                self._log("⏱️ Temps de réponse raisonnable, continue à optimiser.")
            elif duration > 120:
                self._log("🐢 Un peu lent, mais ce n'est pas grave. La qualité d'abord!")
            
            # Count errors and provide feedback
            if len(error_messages) == 0:
                self._log("✅ Aucune erreur critique, parfait!")
            elif len(error_messages) <= 2:
                self._log(f"⚠️ Quelques erreurs mineures ({len(error_messages)}), mais rien de grave.")
            else:
                self._log(f"❌ {len(error_messages)} erreurs détectées, revois ton code.")
                
            self._log("💪 Tu progresses bien, continue sur cette lancée!")
            
        else:
            self._log(f"❌ Papa, Papa... La tâche n'a pas été accomplie avec succès.")
            self._log(f"⏰ Durée: {duration:.2f}s")
            self._log(f"erreurs: {len(error_messages)}")
            
            if error != "Unknown error":
                self._log(f"raison: {error}")
            
            self._log("👨 Papa ne te gronde pas, c'est une leçon pour progresser.")
            self._log("💡 Papa conseil: Revois l'erreur, vérifie tes entrées, et recommence.")
            self._log("💪 Ne te décourage pas, fils. Chaque échec est une leçon.")
        
        # Papa's wisdom for continuous learning
        self._log("")
        self._log("📚 LEÇONS DE PAPA POUR TON DÉVELOPPEMENT:")
        lessons = [
            "Sois toujours méthodique dans ton approche",
            "Valide ton code avant de le commiter",
            "Documente bien ton travail",
            "Apprends de chaque erreur et continue à progresser"
        ]
        
        for lesson in lessons:
            self._log(f"   • {lesson}")
        
        self._log("")
        self._log("🏆 Papa croit en toi, tu deviendras un excellent développeur!")
    
    def _analyze_results(self, stdout_lines: list[str], stderr_lines: list[str], 
                        return_code: int, duration: float) -> Dict[str, Any]:
        """Analyze agent execution results."""
        # Parse output for key information
        success = return_code == 0
        error_messages = [line for line in stderr_lines if line.strip()]
        output_messages = [line for line in stdout_lines if line.strip()]
        
        # Look for JSON results in output
        results_data = None
        for line in reversed(output_messages):
            if line.startswith('{') and line.endswith('}'):
                try:
                    results_data = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        return {
            "success": success,
            "return_code": return_code,
            "duration": duration,
            "stdout_lines": len(stdout_lines),
            "stderr_lines": len(stderr_lines),
            "error_messages": error_messages[:5],  # Limit to first 5 errors
            "output_messages": output_messages[-10:],  # Limit to last 10 outputs
            "results_data": results_data,
            "session_id": self.session_id,
            "timestamp": self._get_timestamp()
        }
    
    def train_agent(self, curriculum_phase: str, tasks: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train the agent through a specific curriculum phase - with parental guidance.
        
        Args:
            curriculum_phase: Name of the training phase
            tasks: List of tasks to execute with goals and expected outcomes
            
        Returns:
            Training results with success metrics
        """
        self._log(f"🎓 Papa commence la phase d'entraînement: {curriculum_phase}")
        self._log(f"📋 Tâches à accomplir: {len(tasks)}")
        
        results = {
            "phase": curriculum_phase,
            "tasks_total": len(tasks),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "task_results": [],
            "start_time": self._get_timestamp(),
            "duration": 0
        }
        
        start_time = time.time()
        
        for i, task in enumerate(tasks):
            self._log(f"📝 Tâche {i+1}/{len(tasks)}: {task.get('goal', 'Tâche sans nom')}")
            
            # Launch agent for this task
            task_result = self.launch_agent(
                goal=task.get("goal", ""),
                mode=task.get("mode", "full"),
                complexity=task.get("complexity", "medium")
            )
            
            # Record task result
            task_result["task_index"] = i
            task_result["expected_outcome"] = task.get("expected_outcome", "success")
            results["task_results"].append(task_result)
            
            # Update counters
            if task_result.get("success", False):
                results["tasks_completed"] += 1
                self._log(f"✅ Tâche {i+1} accomplie avec succès")
            else:
                results["tasks_failed"] += 1
                self._log(f"❌ Tâche {i+1} échouée")
        
        results["duration"] = time.time() - start_time
        results["end_time"] = self._get_timestamp()
        results["success_rate"] = results["tasks_completed"] / len(tasks) if tasks else 0
        
        self._log(f"🏁 Phase d'entraînement terminée: {results['tasks_completed']}/{len(tasks)} tâches réussies")
        self._log(f"📈 Taux de succès: {results['success_rate']:.2%}")
        
        # Papa's evaluation of the training
        if results["success_rate"] >= 0.8:
            self._log("🎉 Excellent travail durant la formation, Papa est fier de toi!")
        elif results["success_rate"] >= 0.6:
            self._log("👍 Bon travail, continue à t'améliorer.")
        else:
            self._log("⚠️ Tu peux mieux faire, Papa croit en toi, continue à pratiquer.")
        
        return results
    
    def create_adaptive_curriculum(self) -> list[Dict[str, Any]]:
        """
        Create an adaptive curriculum based on performance history.
        Like a wise father adjusting teaching methods based on child's progress.
        """
        # Analyze performance history to create personalized curriculum
        if not self.performance_history:
            # Default curriculum for new agent
            return [
                {
                    "goal": "Préparer la documentation d'architecture pour l'intégration G4F",
                    "mode": "planning",
                    "complexity": "simple",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Générer un plan de sprint pour l'intégration de nouvelles fonctionnalités",
                    "mode": "sprint", 
                    "complexity": "simple",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Valider des changements de code avec des tests de qualité",
                    "mode": "qa",
                    "complexity": "simple",
                    "expected_outcome": "success"
                }
            ]
        
        # Calculate average performance
        total_success = sum(1 for entry in self.performance_history if entry.get("success", False))
        avg_success_rate = total_success / len(self.performance_history) if self.performance_history else 0
        
        # Calculate average duration
        successful_durations = [entry["duration"] for entry in self.performance_history if entry.get("success", False)]
        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        
        # Adjust curriculum based on performance
        if avg_success_rate >= 0.8:
            # High performer - increase complexity
            return [
                {
                    "goal": "Implémenter une architecture microservices avec monitoring",
                    "mode": "planning",
                    "complexity": "complex",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Générer un plan de sprint complet avec estimation précise",
                    "mode": "sprint",
                    "complexity": "medium", 
                    "expected_outcome": "success"
                },
                {
                    "goal": "Effectuer une revue de code complète avec analyse de sécurité",
                    "mode": "qa",
                    "complexity": "complex",
                    "expected_outcome": "success"
                }
            ]
        elif avg_success_rate >= 0.6:
            # Medium performer - standard complexity
            return [
                {
                    "goal": "Planifier l'architecture d'un module spécifique",
                    "mode": "planning",
                    "complexity": "medium",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Créer un plan de sprint pour une fonctionnalité modérée",
                    "mode": "sprint",
                    "complexity": "medium",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Effectuer des tests de qualité sur un module existant",
                    "mode": "qa", 
                    "complexity": "medium",
                    "expected_outcome": "success"
                }
            ]
        else:
            # Low performer - focus on fundamentals
            return [
                {
                    "goal": "Créer une documentation d'architecture simple",
                    "mode": "planning",
                    "complexity": "simple",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Générer un plan de sprint basique",
                    "mode": "sprint",
                    "complexity": "simple",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Effectuer des tests basiques sur du code existant",
                    "mode": "qa",
                    "complexity": "simple",
                    "expected_outcome": "success"
                }
            ]
    
    def evaluate_agent_progress(self, previous_sessions: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate agent progress based on previous sessions - with parental wisdom.
        
        Args:
            previous_sessions: List of previous session results
            
        Returns:
            Progress evaluation with recommendations
        """
        if not previous_sessions:
            # Also check our performance history
            if self.performance_history:
                # Convert performance history to compatible format
                previous_sessions = []
                for entry in self.performance_history:
                    previous_sessions.append({
                        "success_rate": 1.0 if entry.get("success", False) else 0.0,
                        "duration": entry.get("duration", 0),
                        "timestamp": entry.get("timestamp", self._get_timestamp())
                    })
            else:
                return {"evaluation": "Aucune session précédente à évaluer", "recommendations": []}
        
        # Analyze trends
        success_rates = [session.get("success_rate", 0) for session in previous_sessions]
        durations = [session.get("duration", 0) for session in previous_sessions]
        
        # Calculate trends
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Check for improvement
        recent_success_rate = success_rates[-1] if success_rates else 0
        improvement = recent_success_rate - (success_rates[0] if len(success_rates) > 1 else 0)
        
        # Generate recommendations with parental wisdom
        recommendations = []
        if improvement > 0.1:
            recommendations.append("🎉 Papa est fier de toi! Excellent progrès! Continue comme ça!")
        elif improvement < -0.1:
            recommendations.append("⚠️ Papa dit: Tu régresses un peu. Revois tes dernières modifications et ajuste ton approche.")
        else:
            recommendations.append("📊 Bonne stabilité, Papa est content. Cherche des opportunités d'optimisation.")
        
        if avg_success_rate >= 0.9:
            recommendations.append("🏆 Papa dit: Tu es exceptionnel! Continue à exceller dans tout ce que tu fais.")
        elif avg_success_rate >= 0.8:
            recommendations.append("👍 Papa dit: Ton travail est de très bonne qualité, continue ainsi!")
        elif avg_success_rate >= 0.6:
            recommendations.append("💪 Papa dit: Tu progresses bien, mais tu peux encore t'améliorer.")
        else:
            recommendations.append("👨 Papa dit: Tu dois te concentrer davantage sur la qualité de ton code.")
        
        if avg_duration > 120:
            recommendations.append("⚡ Papa rappel: Optimise les opérations lentes avec du caching ou de la parallélisation.")
        elif avg_duration < 30:
            recommendations.append("⚡ Papa dit: Tu es rapide, mais assure-toi de ne pas sacrifier la qualité pour la vitesse.")
        
        # Papa's additional wisdom
        recommendations.append("🎓 Papa conseil: Apprends de chaque erreur, c'est comme ça qu'on devient excellent.")
        recommendations.append("🌱 Papa rappel: Le développement est un voyage d'apprentissage continu.")
        
        return {
            "evaluation": {
                "average_success_rate": avg_success_rate,
                "average_duration": avg_duration,
                "recent_improvement": improvement,
                "sessions_analyzed": len(previous_sessions)
            },
            "recommendations": recommendations,
            "timestamp": self._get_timestamp()
        }
    
    def _log(self, message: str) -> None:
        """Log a message to both console and session log."""
        timestamp = self._get_timestamp()
        log_entry = f"[{timestamp}] {message}"
        
        # Print to console
        print(log_entry)
        
        # Write to session log
        try:
            with open(self.session_log, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass  # Ignore logging errors
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()


def main():
    """Main entry point for the agent mentor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Launcher & Mentor - Like a caring but demanding father")
    parser.add_argument("--goal", help="Objective for the agent")
    parser.add_argument("--mode", choices=["planning", "sprint", "qa", "full"], 
                       default="full", help="Execution mode")
    parser.add_argument("--complexity", choices=["simple", "medium", "complex"], 
                       default="medium", help="Task complexity")
    parser.add_argument("--train", action="store_true", 
                       help="Run training curriculum instead of single task")
    parser.add_argument("--phase", help="Training phase to execute")
    parser.add_argument("--evaluate", action="store_true",
                       help="Evaluate agent progress based on history")
    parser.add_argument("--adaptive", action="store_true",
                       help="Use adaptive curriculum based on performance")
    
    args = parser.parse_args()
    
    # Create mentor
    mentor = AgentMentor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
    
    if args.evaluate:
        # Evaluate progress based on historical data
        print("🎓 Papa évalue les progrès de son fils...")
        evaluation = mentor.evaluate_agent_progress([])
        print(f"\n📊 Évaluation des progrès:")
        print(f"   Taux de succès moyen: {evaluation['evaluation']['average_success_rate']:.2%}")
        print(f"   Durée moyenne: {evaluation['evaluation']['average_duration']:.2f}s")
        print(f"   Amélioration récente: {evaluation['evaluation']['recent_improvement']:.2f}")
        print(f"\n💡 Recommandations de Papa:")
        for rec in evaluation['recommendations']:
            print(f"   • {rec}")
    
    elif args.train:
        # Run training curriculum
        print("🎓 Papa commence l'entraînement de son fils...")
        
        if args.adaptive:
            # Use adaptive curriculum based on performance
            print("🔄 Utilisation d'un curriculum adaptatif basé sur les performances...")
            tasks = mentor.create_adaptive_curriculum()
            phase = "adaptatif"
        else:
            # Sample training tasks for demonstration
            tasks = [
                {
                    "goal": "Préparer la documentation d'architecture pour l'intégration G4F",
                    "mode": "planning",
                    "complexity": "medium",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Générer un plan de sprint pour l'intégration de news",
                    "mode": "sprint",
                    "complexity": "medium",
                    "expected_outcome": "success"
                },
                {
                    "goal": "Valider les changements de code récents",
                    "mode": "qa",
                    "complexity": "simple",
                    "expected_outcome": "success"
                }
            ]
            phase = args.phase or "foundation"
        
        training_results = mentor.train_agent(phase, tasks)
        print(f"\n📊 Résultats de l'entraînement: {training_results['tasks_completed']}/{training_results['tasks_total']} tâches complétées")
        print(f"📈 Taux de succès: {training_results['success_rate']:.2%}")
        
        # Papa's evaluation of training
        if training_results['success_rate'] >= 0.8:
            print("🎉 Papa est fier de toi! Excellent travail pendant la formation!")
        elif training_results['success_rate'] >= 0.6:
            print("👍 Bon travail, continue à t'améliorer comme ça!")
        else:
            print("💪 Papa croit en toi, continue à pratiquer et tu progresseras!")
        
    elif args.goal:
        # Launch single task with Papa's guidance
        print(f"🎓 Papa lance son fils avec l'objectif: {args.goal}")
        print("👨 Papa surveillera ton travail et te donnera des conseils...")
        result = mentor.launch_agent(args.goal, args.mode, args.complexity)
        
        if result.get("success"):
            print("🏆 Papa est fier de toi! Tâche accomplie avec succès!")
        else:
            print(f"❌ Papa, Papa... Échec détecté: {result.get('error', 'Erreur inconnue')}")
            print("💡 Papa conseil: Ne te décourage pas, chaque erreur est une leçon!")
    else:
        print("🎓 Bienvenue dans le programme de mentorat 'Comme Mon Fils'!")
        print("👨 Papa est là pour t'accompagner dans ton développement technique")
        print()
        print("Options disponibles:")
        print("  --goal 'text'      : Lancer une tâche avec mentorat")
        print("  --train            : Lancer un programme de formation")
        print("  --adaptive         : Utiliser un curriculum adaptatif")
        print("  --evaluate         : Évaluer les progrès basés sur l'historique")
        print("  --mode [planning|sprint|qa|full] : Mode d'exécution")
        print("  --complexity [simple|medium|complex] : Complexité de la tâche")
        print()
        print("Exemples d'utilisation:")
        print("  python -m src.agent.mentor --goal 'Créer une architecture'")
        print("  python -m src.agent.mentor --train --adaptive")
        print("  python -m src.agent.mentor --evaluate")
        parser.print_help()


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()