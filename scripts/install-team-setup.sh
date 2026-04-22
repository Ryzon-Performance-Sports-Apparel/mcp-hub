#!/usr/bin/env bash
# install-team-setup.sh — Ryzon Knowledge Ops · Team Setup Installer
#
# Idempotent installer für Sophie, Luca, Simon (macOS).
# Installiert Dependencies, klont Repos, legt Folder-Struktur an.
#
# Usage:
#   curl -fsSL <url>/install-team-setup.sh | bash
#   oder:
#   chmod +x install-team-setup.sh && ./install-team-setup.sh
#
set -euo pipefail

# ─── Colors & Logging ───────────────────────────────────────────────────────

readonly C_RESET='\033[0m'
readonly C_BLUE='\033[0;34m'
readonly C_GREEN='\033[0;32m'
readonly C_YELLOW='\033[0;33m'
readonly C_RED='\033[0;31m'

info()    { printf "${C_BLUE}ℹ  %s${C_RESET}\n" "$*"; }
ok()      { printf "${C_GREEN}✓  %s${C_RESET}\n" "$*"; }
warn()    { printf "${C_YELLOW}⚠  %s${C_RESET}\n" "$*"; }
error()   { printf "${C_RED}✗  %s${C_RESET}\n" "$*" >&2; }
step()    { printf "\n${C_BLUE}━━━ %s ━━━${C_RESET}\n" "$*"; }

# ─── Config ─────────────────────────────────────────────────────────────────

readonly CONTEXT_DIR="${HOME}/Documents/projects/context"
readonly ORG="Ryzon-Performance-Sports-Apparel"
readonly REPO_AI_CONTEXT="${ORG}/ai-context"
readonly REPO_VAULT="${ORG}/ryzon-context-vault"

# ─── Preflight ──────────────────────────────────────────────────────────────

step "Preflight-Checks"

if [[ "$(uname)" != "Darwin" ]]; then
  error "Dieses Script ist aktuell nur für macOS getestet. Abbruch."
  exit 1
fi

# ─── Homebrew ───────────────────────────────────────────────────────────────

step "Homebrew"

if ! command -v brew >/dev/null 2>&1; then
  warn "Homebrew nicht installiert."
  read -p "Jetzt installieren? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  else
    error "Homebrew benötigt. Abbruch."
    exit 1
  fi
fi
ok "Homebrew: $(brew --version | head -1)"

# ─── Git + gh CLI ───────────────────────────────────────────────────────────

step "Git und GitHub CLI"

for tool in git gh; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    info "Installiere $tool..."
    brew install "$tool"
  fi
  ok "$tool: $("$tool" --version | head -1)"
done

# GitHub-Auth prüfen
if ! gh auth status >/dev/null 2>&1; then
  warn "GitHub-CLI ist nicht authentifiziert."
  info "Starte Auth-Flow (öffnet Browser)..."
  gh auth login
fi
ok "GitHub-Auth: aktiv"

# Prüfe Org-Zugang
if ! gh api "orgs/${ORG}" >/dev/null 2>&1; then
  error "Kein Zugang zur ${ORG}-Org. Bitte Zugang anfragen bei Simon."
  exit 1
fi
ok "Ryzon-Org-Zugang: OK"

# ─── Node + obsidian-cli ────────────────────────────────────────────────────

step "Node.js und obsidian-cli"

if ! command -v node >/dev/null 2>&1; then
  info "Installiere Node.js..."
  brew install node
fi
ok "Node: $(node --version)"

if ! command -v obsidian-cli >/dev/null 2>&1; then
  info "Installiere obsidian-cli global (npm)..."
  npm install -g obsidian-cli
fi
ok "obsidian-cli: installiert"

# ─── Obsidian.app ───────────────────────────────────────────────────────────

step "Obsidian"

if [[ ! -d "/Applications/Obsidian.app" ]]; then
  info "Installiere Obsidian.app..."
  brew install --cask obsidian
fi
ok "Obsidian: /Applications/Obsidian.app vorhanden"

# ─── Python ─────────────────────────────────────────────────────────────────

step "Python"

if ! command -v python3 >/dev/null 2>&1; then
  info "Installiere Python..."
  brew install python3
fi
ok "Python: $(python3 --version)"

# ─── User-Identität ─────────────────────────────────────────────────────────

step "Wer bist du?"

DEFAULT_USER=""
if command -v git >/dev/null 2>&1; then
  DEFAULT_USER="$(git config --global user.email 2>/dev/null | cut -d@ -f1 | tr '[:upper:]' '[:lower:]' || true)"
  # Normalize bekannte Namen
  case "$DEFAULT_USER" in
    *simon*) DEFAULT_USER="simon" ;;
    *sophie*) DEFAULT_USER="sophie" ;;
    *luca*) DEFAULT_USER="luca" ;;
    *mario*) DEFAULT_USER="mario" ;;
  esac
fi

while true; do
  if [[ -n "$DEFAULT_USER" ]]; then
    read -p "Dein Nutzername (simon/sophie/luca/mario) [${DEFAULT_USER}]: " USER_INPUT
    USERNAME="${USER_INPUT:-$DEFAULT_USER}"
  else
    read -p "Dein Nutzername (simon/sophie/luca/mario): " USERNAME
  fi
  case "$USERNAME" in
    simon|sophie|luca|mario) break ;;
    *) warn "Bitte einen der 4 Namen wählen (simon/sophie/luca/mario)." ;;
  esac
done
ok "Nutzername: $USERNAME"

# ─── Folder-Struktur ────────────────────────────────────────────────────────

step "Folder-Struktur anlegen"

mkdir -p "$CONTEXT_DIR"
ok "Erstellt: $CONTEXT_DIR"

# Private-Folder (NICHT git, nur lokal)
PRIVATE_DIR="${CONTEXT_DIR}/private/${USERNAME}"
mkdir -p "${PRIVATE_DIR}/1on1" "${PRIVATE_DIR}/hr" "${PRIVATE_DIR}/strategic"
ok "Erstellt: private/${USERNAME}/ (1on1 · hr · strategic)"

# README in private/
cat > "${CONTEXT_DIR}/private/README.md" <<'EOF'
# Private Folder

**Dieser Folder ist NICHT git-tracked.**

Inhalte hier bleiben lokal auf deinem Laptop. Sie werden nie zu GitHub hochgeladen.

Geeignet für:
- 1on1-Notizen
- HR-Themen
- Persönliche strategische Überlegungen, die nicht team-shared werden sollen

Wenn du ein File aus versehen hier ablegen willst, das eigentlich team-shared gehört,
kopiere es nach `ryzon-context-vault/<dein-username>/` oder `shared/`.
EOF

# ─── Repos klonen ───────────────────────────────────────────────────────────

step "Repos klonen"

# ai-context
if [[ ! -d "${CONTEXT_DIR}/ai-context" ]]; then
  info "Klone ${REPO_AI_CONTEXT}..."
  cd "$CONTEXT_DIR"
  gh repo clone "$REPO_AI_CONTEXT"
  ok "ai-context geklont"
else
  info "ai-context existiert bereits, pulle..."
  cd "${CONTEXT_DIR}/ai-context" && git pull --ff-only || warn "Pull fehlgeschlagen, prüfe manuell"
  ok "ai-context aktualisiert"
fi

# ryzon-context-vault
if [[ ! -d "${CONTEXT_DIR}/ryzon-context-vault" ]]; then
  info "Klone ${REPO_VAULT}..."
  cd "$CONTEXT_DIR"
  if gh repo clone "$REPO_VAULT"; then
    ok "ryzon-context-vault geklont"
  else
    error "Konnte ${REPO_VAULT} nicht klonen. Existiert das Repo?"
    warn "Falls das Repo noch nicht existiert, bitte bei Simon nachfragen."
    exit 1
  fi
else
  info "ryzon-context-vault existiert, pulle..."
  cd "${CONTEXT_DIR}/ryzon-context-vault" && git pull --ff-only || warn "Pull fehlgeschlagen, prüfe manuell"
  ok "ryzon-context-vault aktualisiert"
fi

# User-Vault-Folder sicherstellen
USER_VAULT="${CONTEXT_DIR}/ryzon-context-vault/${USERNAME}"
if [[ ! -d "$USER_VAULT" ]]; then
  warn "Dein Vault-Folder ${USERNAME}/ existiert nicht im Repo — lege an..."
  mkdir -p "$USER_VAULT"/{notes,learnings,analyses,granola,meetings}
  echo "# ${USERNAME}'s Vault" > "${USER_VAULT}/README.md"
  cd "${CONTEXT_DIR}/ryzon-context-vault"
  git add "${USERNAME}/"
  git commit -m "init: ${USERNAME} vault folders" || true
  git push || warn "Push fehlgeschlagen — manuell pushen"
  ok "Vault-Folder ${USERNAME}/ erstellt und gepusht"
fi

# ─── Summary + Manuelle Schritte ────────────────────────────────────────────

step "Installation fertig — Was du jetzt NOCH tun musst"

cat <<EOF

${C_GREEN}✓ Automatische Installation abgeschlossen.${C_RESET}

Folder-Struktur unter ${C_BLUE}${CONTEXT_DIR}${C_RESET}:
  ai-context/                ← git-Repo, strategisch
  ryzon-context-vault/       ← git-Repo, operativ
  ├── ${USERNAME}/           ← DEIN Obsidian-Vault (öffne NUR diesen)
  └── shared/                ← Team-Scratchpad
  private/${USERNAME}/       ← NICHT git, nur lokal

${C_YELLOW}Manuelle Schritte (3 Stück):${C_RESET}

${C_BLUE}① Obsidian-Vault öffnen${C_RESET}
   Starte Obsidian.app und öffne den Folder:
   ${CONTEXT_DIR}/ryzon-context-vault/${USERNAME}

   ⚠  Wichtig: öffne NUR deinen Folder ("${USERNAME}/"), NICHT den Repo-Root.
   So funktionieren Wiki-Links und der Graph-View richtig.

${C_BLUE}② Claude App — Plugin installieren${C_RESET}
   1. Öffne Claude App → Customize → Directory → Plugins → Personal
   2. Klick "Upload plugin"
   3. Lade die ZIP-Datei ryzon-knowledge-ops.zip hoch
      (Simon schickt dir den Link oder du findest sie im mcp-Repo)
   4. Aktiviere das Plugin

${C_BLUE}③ Claude Project "Ryzon Knowledge Ops" erstellen${C_RESET}
   1. Claude App → New Project → Name: "Ryzon Knowledge Ops"
   2. Aktiviere Plugin "ryzon-knowledge-ops"
   3. Connectors hinzufügen:
      - GitHub: beide Repos (ai-context + ryzon-context-vault)
      - Google Drive: dein Drive
   4. Project Instructions einfügen:
      cat ${CONTEXT_DIR}/ai-context/schema/claude-project-instructions.md
      (oder aus docs/knowledge-setup/claude-project-instructions-template.md im mcp-Repo)
   5. Teste: "/capture learning Das Install-Script hat funktioniert"

${C_YELLOW}Erste Nutzung:${C_RESET}
  - "/pull sales" — lädt Kontext
  - "/capture learning <content>" — speichert Insight
  - "/decision <frage>" — dokumentiert Entscheidung
  - "/distill" — destilliert lange Session

${C_YELLOW}Bei Problemen:${C_RESET}
  Slack-Channel: #knowledge-ops-experiment
  Oder direkt Simon pingen.

EOF
