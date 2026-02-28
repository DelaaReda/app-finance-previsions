# LEGACY_POLICY.md

## Principle
Ne rien supprimer. Conserver l'historique en déplaçant dans `legacy/` (ou repo legacy dédié).

## Legacy Move Checklist
1. Identifier le bloc obsolète
2. Vérifier qu'il n'est plus appelé (grep/import/references)
3. Déplacer vers `legacy/<date>-<topic>/...`
4. Ajouter un `README.md` expliquant:
   - origine
   - raison du déplacement
   - remplaçant actif
5. Mettre à jour `ARCHITECTURE_MAP.md`
6. Vérifier démarrage + smoke tests

## Naming Convention
- Dossier: `legacy/YYYY-MM-DD_<scope>`
- Fichier note: `LEGACY_NOTE.md`

## Forbidden
- `rm -rf` destructif sur code métier
- Suppression silencieuse sans note de migration
