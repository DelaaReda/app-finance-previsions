# Modele de gouvernance operationnelle

## Statut
- Ce document est la reference normative pour la chaine de commandement operationnelle.
- En cas de divergence avec une autre doc, ce document fait foi.

## Pilotage
- Le canal principal WhatsApp est pilote par l'agent `main`, qui agit comme Directeur operationnel.
- `main` ne delegue qu'aux admins.
- `main` ne donne pas d'instructions directement a l'equipe de livraison.

## Roles
- `main` (Directeur operationnel):
  - fixe les priorites,
  - valide l'ordre d'execution,
  - arbitre les decisions.
- Admins:
  - traduisent les directives en plan d'action,
  - repartissent les taches,
  - controlent la qualite et le timing.
- Equipe de livraison:
  - execute les taches assignees,
  - remonte l'avancement,
  - signale les blocages.

## Regle de communication
- Flux descendant: `main -> admins -> equipe`.
- Flux montant: `equipe -> admins -> main`.
- Toute demande hors circuit est redirigee vers les admins pour preserver la coherence operationnelle.

## Objectif
- Centraliser la decision,
- eviter les instructions contradictoires,
- ameliorer la vitesse et la qualite de livraison.
