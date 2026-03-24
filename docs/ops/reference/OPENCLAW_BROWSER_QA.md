# OpenClaw Browser — Smoke QA (frontend)

Ce guide couvre la vérification visuelle/DOM/réseau avec l’interface navigateur intégrée à OpenClaw.

## Objectif

- Vérifier rapidement qu’une page charge bien les styles et scripts (sans retour 404 silencieux).
- Capturer une preuve visuelle (snapshot/screenshot).
- Détecter les erreurs JS console, réseau et DOM avant de clôturer un lot frontend.

## Pré-requis

- Frontend actif sur `http://127.0.0.1:5173` ou URL correspondante.
- Backend actif si la page consomme des endpoints live.
- OpenClaw CLI installé localement.

## Flux de validation (par défaut)

1. Vérifier le navigateur:

```bash
openclaw browser status --json
```

2. Ouvrir la page cible:

```bash
openclaw browser open "http://127.0.0.1:5173/index.html"
```

3. Optionnel: redimensionner la vue:

```bash
openclaw browser resize 1440 1024
```

4. Attendre le chargement DOM:

```bash
openclaw browser wait --load domcontentloaded
```

5. Inspecter le DOM:

```bash
openclaw browser snapshot --labels --limit 200
```

6. Vérifier réseau + erreurs:

```bash
openclaw browser requests --json
openclaw browser console --level error
openclaw browser errors
```

7. Capture écran:

```bash
openclaw browser screenshot --full-page
```

8. Vérifier que le CSS principal existe bien côté runtime:

```bash
openclaw browser evaluate --fn "() => ({sheetsCount: document.styleSheets.length, links: Array.from(document.styleSheets).map(s => s.href || 'inline').filter(Boolean).slice(0,10), fontFamily: getComputedStyle(document.body).fontFamily})"
```

9. Fermer le tab de test quand fini:

```bash
openclaw browser close
```

## Exemple de sortie attendue (indicateurs)

- `requests` doit contenir les ressources importantes en HTTP 200:
  - `platform/style.css`
  - `platform/design-tokens.css`
  - composants HTML de `/components/...`
- `console` sans erreurs bloquantes JS.
- Snapshot non vide avec sections attendues (`News Feed`, `Forecasts`, `Portfolio`, etc).

## Commandes utilitaires

- Lister les tabs ouvertes:

```bash
openclaw browser tabs
```

- Voir la cible active (si plusieurs tabs):

```bash
openclaw browser focus <targetId>
```

- Arrêter/relancer le browser dédié:

```bash
openclaw browser stop
openclaw browser start
```

## Note d’usage

- Quand une page ne charge pas correctement, relancer `openclaw browser stop && openclaw browser start`, puis répéter le flux depuis l’étape 2.
- Conserver le lien de la capture (`MEDIA:~/.openclaw/media/...`) dans la preuve de lot si le lot frontend est considéré terminé.
