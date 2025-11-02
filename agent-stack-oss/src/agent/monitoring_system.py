#!/usr/bin/env python3
"""
Système de monitoring et de feedback en temps réel pour l'agent
"""

from __future__ import annotations
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import threading
import queue

@dataclass
class MonitorEvent:
    """Événement de monitoring"""
    timestamp: str
    node: str
    event_type: str  # 'start', 'progress', 'warning', 'error', 'complete'
    message: str
    details: Dict[str, Any]
    session_id: str

@dataclass
class AgentPerformanceMetrics:
    """Métriques de performance de l'agent"""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[float] = None
    nodes_executed: List[str] = None
    errors: int = 0
    warnings: int = 0
    completed_successfully: bool = False
    goal: str = ""
    mode: str = ""
    complexity: str = ""

class AgentMonitor:
    """
    Système de monitoring en temps réel pour observer les performances de l'agent.
    Comme un père qui surveille son fils en train de travailler.
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.monitor_dir = self.project_root / "data" / "monitoring"
        self.monitor_dir.mkdir(parents=True, exist_ok=True)
        
        self.events_log = self.monitor_dir / "events.jsonl"  # Line-delimited JSON
        self.metrics_log = self.monitor_dir / "metrics.json"
        
        # Pour le monitoring en temps réel
        self.event_queue = queue.Queue()
        self.metrics: Optional[AgentPerformanceMetrics] = None
        self.session_active = False
        self.monitoring_thread = None
        
        # Démarrer le thread de monitoring
        self.start_monitoring()
    
    def start_monitoring(self):
        """Démarrer le monitoring en arrière-plan."""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitoring_thread.start()
    
    def start_session(self, session_id: str, goal: str, mode: str = "full", complexity: str = "medium"):
        """Démarrer une session de monitoring."""
        self.session_active = True
        self.metrics = AgentPerformanceMetrics(
            session_id=session_id,
            start_time=self._get_timestamp(),
            goal=goal,
            mode=mode,
            complexity=complexity,
            nodes_executed=[]
        )
        
        self.log_event(session_id, "monitor", "session_start", f"Démarrage de la session pour: {goal}")
    
    def stop_session(self, completed_successfully: bool = False):
        """Arrêter une session de monitoring."""
        if self.metrics:
            self.metrics.end_time = self._get_timestamp()
            self.metrics.duration = time.time() - datetime.fromisoformat(self.metrics.start_time.replace("Z", "+00:00")).timestamp()
            self.metrics.completed_successfully = completed_successfully
            
            # Sauvegarder les métriques
            with open(self.metrics_log, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.metrics), f, ensure_ascii=False, indent=2)
        
        self.session_active = False
        self.log_event("system", "monitor", "session_end", "Session terminée")
    
    def log_event(self, session_id: str, node: str, event_type: str, message: str, 
                  details: Optional[Dict[str, Any]] = None):
        """Enregistrer un événement de monitoring."""
        event = MonitorEvent(
            timestamp=self._get_timestamp(),
            node=node,
            event_type=event_type,
            message=message,
            details=details or {},
            session_id=session_id
        )
        
        # Ajouter à la queue pour traitement asynchrone
        self.event_queue.put(event)
    
    def _process_event(self, event: MonitorEvent):
        """Traiter un événement de monitoring."""
        # Sauvegarder dans le fichier d'événements
        with open(self.events_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + '\n')
        
        # Mettre à jour les métriques
        if self.metrics and self.metrics.session_id == event.session_id:
            if event.event_type == "error":
                self.metrics.errors += 1
            elif event.event_type == "warning":
                self.metrics.warnings += 1
            
            if event.node not in self.metrics.nodes_executed:
                self.metrics.nodes_executed.append(event.node)
        
        # Afficher en temps réel
        self._display_event(event)
    
    def _display_event(self, event: MonitorEvent):
        """Afficher un événement en temps réel."""
        print(f"[{event.timestamp.split('T')[1].split('.')[0]}] [{event.event_type.upper()}] {event.node}: {event.message}")
    
    def _monitor_loop(self):
        """Boucle de monitoring principale."""
        while True:
            try:
                # Récupérer les événements avec un timeout
                event = self.event_queue.get(timeout=1.0)
                self._process_event(event)
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                # Continue même en cas d'erreur
                continue
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Obtenir les métriques en temps réel."""
        if not self.metrics:
            return {"message": "Aucune session active"}
        
        current_time = time.time()
        start_time = datetime.fromisoformat(self.metrics.start_time.replace("Z", "+00:00")).timestamp()
        elapsed_time = current_time - start_time
        
        return {
            "session_id": self.metrics.session_id,
            "elapsed_time": elapsed_time,
            "nodes_executed": len(self.metrics.nodes_executed),
            "errors": self.metrics.errors,
            "warnings": self.metrics.warnings,
            "status": "active" if self.session_active else "completed",
            "current_nodes": self.metrics.nodes_executed,
            "goal": self.metrics.goal
        }
    
    def generate_performance_report(self) -> str:
        """Générer un rapport de performance détaillé."""
        if not self.metrics:
            return "Aucune session terminée à analyser"
        
        report_parts = [
            "# RAPPORT DE PERFORMANCE DE L'AGENT",
            f"Session ID: {self.metrics.session_id}",
            f"Objectif: {self.metrics.goal}",
            f"Mode: {self.metrics.mode}",
            f"Complexité: {self.metrics.complexity}",
            f"Début: {self.metrics.start_time}",
            f"Fin: {self.metrics.end_time}",
            f"Durée: {self.metrics.duration:.2f}s" if self.metrics.duration else "En cours",
            f"Succès: {'Oui' if self.metrics.completed_successfully else 'Non'}",
            "",
            "## MÉTRIQUES DÉTAILLÉES",
            f"- Noeuds exécutés: {len(self.metrics.nodes_executed)}",
            f"- Erreurs: {self.metrics.errors}",
            f"- Avertissements: {self.metrics.warnings}",
            f"- Noeuds: {', '.join(self.metrics.nodes_executed)}",
            "",
            "## FEEDBACK PARENTAL",
        ]
        
        # Feedback basé sur les performances
        if self.metrics.errors == 0:
            report_parts.append("✅ Excellent travail! Aucune erreur détectée.")
        elif self.metrics.errors <= 2:
            report_parts.append("⚠️ Bon travail, mais attention aux quelques erreurs.")
        else:
            report_parts.append(f"❌ Attention, {self.metrics.errors} erreurs détectées. Revois ton code.")
        
        if self.metrics.warnings == 0:
            report_parts.append("✅ Parfait! Aucun avertissement.")
        elif self.metrics.warnings <= 3:
            report_parts.append("ℹ️ Peu d'avertissements, c'est bien.")
        else:
            report_parts.append(f"ℹ️ {self.metrics.warnings} avertissements détectés. Peut être amélioré.")
        
        # Feedback sur la durée
        if self.metrics.duration:
            if self.metrics.duration < 60:
                report_parts.append("⚡ Très rapide! Excellent timing.")
            elif self.metrics.duration < 180:
                report_parts.append("⏱️ Temps d'exécution raisonnable.")
            else:
                report_parts.append("🐢 Un peu lent. Pense à optimiser.")
        
        # Feedback sur le succès
        if self.metrics.completed_successfully:
            report_parts.append("🎉 Mission accomplie avec succès!")
        else:
            report_parts.append("❌ Échec de la mission. Revois ta stratégie.")
        
        # Recommandations
        report_parts.extend([
            "",
            "## RECOMMANDATIONS",
            "- Continue à améliorer la qualité du code",
            "- Optimise les performances quand possible",
            "- Pense à la sécurité et à l'architecture",
            "- Apprends de chaque erreur",
            "- Sois méthodique et patient"
        ])
        
        return "\n".join(report_parts)
    
    def _get_timestamp(self) -> str:
        """Obtenir l'horodatage actuel."""
        return datetime.now(timezone.utc).isoformat()

class EnhancedMentor:
    """
    Mentor perfectionné qui combine monitoring et mentorat.
    """
    
    def __init__(self, project_root: str = "."):
        self.monitor = AgentMonitor(project_root)
        self.mentorship_program = None
        try:
            from .mentorship_program import AgentMentorshipProgram
            self.mentorship_program = AgentMentorshipProgram(project_root)
        except ImportError:
            print("[mentor] Programme de mentorat non disponible")
    
    def monitor_session(self, session_id: str, goal: str, mode: str = "full", complexity: str = "medium"):
        """Démarrer le monitoring d'une session."""
        self.monitor.start_session(session_id, goal, mode, complexity)
    
    def end_session(self, completed_successfully: bool = False) -> str:
        """Terminer une session et générer un rapport."""
        self.monitor.stop_session(completed_successfully)
        
        report = self.monitor.generate_performance_report()
        
        # Si le programme de mentorat est disponible, l'utiliser aussi
        if self.mentorship_program and self.monitor.metrics:
            try:
                dummy_result = {
                    "session_id": self.monitor.metrics.session_id,
                    "goal": self.monitor.metrics.goal,
                    "mode": self.monitor.metrics.mode,
                    "success": completed_successfully,
                    "duration": self.monitor.metrics.duration or 0,
                    "tests": {"standard_tests": {}, "architecture_validation": {}, "security_checks": {}}
                }
                mentor_feedback = self.mentorship_program.provide_mentorship_feedback(dummy_result)
                report += f"\n\n{mentor_feedback}"
            except Exception as e:
                print(f"[mentor] Erreur dans le programme de mentorat: {e}")
        
        return report

# Commande CLI pour le monitoring
def cli_monitoring():
    """Interface CLI pour le monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring de l'agent")
    parser.add_argument("--start-session", help="Démarrer une session de monitoring")
    parser.add_argument("--goal", help="Objectif de la session")
    parser.add_argument("--report", action="store_true", help="Générer un rapport de performance")
    parser.add_argument("--metrics", action="store_true", help="Afficher les métriques en temps réel")
    
    args = parser.parse_args()
    
    monitor = AgentMonitor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
    
    if args.start_session:
        if args.goal:
            monitor.start_session(args.start_session, args.goal)
            print(f"✅ Session démarrée: {args.start_session} pour '{args.goal}'")
        else:
            print("Erreur: --goal requis avec --start-session")
    
    elif args.report:
        report = monitor.generate_performance_report()
        print(report)
        
    elif args.metrics:
        metrics = monitor.get_real_time_metrics()
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    cli_monitoring()