# AGENT_WORKFLOW.md

## Team Roles (Lean Solo Product)
1. Product Owner (human + orchestrator)
2. Prioritization Analyst
3. Product/Data Analyst
4. Architect/Tech Lead
5. Backend Engineer
6. Frontend Engineer
7. Data Engineer (light)
8. QA Pragmatique
9. Performance & Reliability (cache/loading)
10. Research & Continuous Improvement

## Definition of Done (DoD)
Une tâche est DONE seulement si:
- code/document modifié
- test/commande de validation exécuté
- preuve partagée (sortie commande, endpoint OK, capture)
- impact décrit (ce qui change pour l'utilisateur)
- rollback simple possible

## Ticket Template (Mandatory)
### Ticket ID
### Contexte
### Objectif
### Fichiers ciblés
### Critères d'acceptation
### Commandes de validation
### Out of scope
### Risques

## Agent Response Template (Mandatory)
- Résumé des changements
- Fichiers modifiés
- Commandes exécutées + résultat
- Limites connues
- Next step recommandé

## Execution Rules
- WIP max: 2 tickets
- Taille ticket: 2-4h
- Si >4h: split obligatoire
- Pas de refacto large sans ticket dédié
- Pas de suppression; déplacement vers `legacy/` uniquement
