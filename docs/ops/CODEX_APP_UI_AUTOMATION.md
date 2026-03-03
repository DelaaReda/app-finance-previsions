# Codex App UI Automation (macOS)

Objectif: injecter des messages dans l'app Codex (desktop) sans passer par `codex` CLI.

## Composants

- `scripts/codex_app_send_message_mac.sh`
  - Injection directe d'un message via `osascript` + collage clavier.
- `scripts/codex_app_enqueue_message.sh`
  - Place un message dans une file locale.
- `scripts/codex_app_queue_worker.sh`
  - Consomme la file et envoie vers l'app Codex.
- `scripts/codex_app_install_launchagent.sh`
  - Installe un LaunchAgent `launchd` pour exécuter le worker en boucle.
- `scripts/codex_app_uninstall_launchagent.sh`
  - Supprime le LaunchAgent.

## Prerequis

- macOS
- App Codex installée
- `System Settings > Privacy & Security > Accessibility`:
  - autoriser Terminal (ou iTerm) a controler l'ordinateur

## Envoi direct (test)

```bash
bash scripts/codex_app_send_message_mac.sh --message "Ping depuis automation" --chat-mode same
```

Nouveau chat a chaque envoi:

```bash
bash scripts/codex_app_send_message_mac.sh --message "Nouveau test" --chat-mode new
```

## Queue + worker

Ajouter un message dans la queue:

```bash
bash scripts/codex_app_enqueue_message.sh --message "Analyse BATCH-06 et fais un resume en 5 points"
```

Traiter la queue manuellement:

```bash
bash scripts/codex_app_queue_worker.sh --max 2
```

Etat runtime:

- Queue: `runtime/codex-app-automation/queue/`
- Envoyes: `runtime/codex-app-automation/sent/`
- Echecs: `runtime/codex-app-automation/failed/`
- Logs: `runtime/codex-app-automation/worker.log`

## Installation automation launchd

```bash
bash scripts/codex_app_install_launchagent.sh --interval 45 --chat-mode same --max 3
```

Verifier:

```bash
launchctl list | grep codex-app-injector
```

Desinstaller:

```bash
bash scripts/codex_app_uninstall_launchagent.sh
```

## Supervision périodique (prompt auto)

Installe 2 jobs launchd:
- worker d'envoi queue -> Codex
- scheduler qui enfile le prompt de supervision à cadence fixe

```bash
bash scripts/codex_app_install_supervision_schedule.sh \
  --bundle-dir "$HOME/.codex-app-automation" \
  --worker-interval 45 \
  --schedule-interval 14400 \
  --chat-mode same \
  --max 3
```

Le prompt utilisé:
- `docs/ops/prompts/CODEX_SUPERVISION_SAME_PROMPT.txt`

Note:
- L'installateur déploie un bundle exécutable dans `~/.codex-app-automation` pour éviter les restrictions launchd sur les dossiers protégés (ex: `Documents`).

Envoi manuel immédiat du prompt supervision:

```bash
bash scripts/codex_app_enqueue_supervision_prompt.sh --force
```

Désinstaller les 2 jobs:

```bash
bash scripts/codex_app_uninstall_supervision_schedule.sh
```

## Limites connues

- C'est de l'automation UI: si la zone de saisie n'est pas focus, l'injection peut echouer.
- Pour une fiabilite max, garder une fenetre Codex ouverte au premier plan pendant les tests initiaux.
