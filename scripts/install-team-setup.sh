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

# ANSI-Escapes via $'...' — so funktionieren sie sowohl in printf als auch in cat <<EOF
readonly C_RESET=$'\033[0m'
readonly C_BLUE=$'\033[0;34m'
readonly C_GREEN=$'\033[0;32m'
readonly C_YELLOW=$'\033[0;33m'
readonly C_RED=$'\033[0;31m'

info()    { printf "${C_BLUE}ℹ  %s${C_RESET}\n" "$*"; }
ok()      { printf "${C_GREEN}✓  %s${C_RESET}\n" "$*"; }
warn()    { printf "${C_YELLOW}⚠  %s${C_RESET}\n" "$*"; }
error()   { printf "${C_RED}✗  %s${C_RESET}\n" "$*" >&2; }
step()    { printf "\n${C_BLUE}━━━ %s ━━━${C_RESET}\n" "$*"; }

# ─── Config ─────────────────────────────────────────────────────────────────

# CONTEXT_DIR kann via Env-Var überschrieben werden für Testing:
#   CONTEXT_DIR=/tmp/test-install ./install-team-setup.sh
readonly CONTEXT_DIR="${CONTEXT_DIR:-${HOME}/Documents/projects/context}"
readonly ORG="Ryzon-Performance-Sports-Apparel"
readonly REPO_GROWTH_NEXUS="${ORG}/growth-nexus"
readonly REPO_VAULT="${ORG}/ryzon-context-vault"

# Skip-Flags für Testing (CI oder wiederholte Test-Runs)
readonly SKIP_DEPS="${SKIP_DEPS:-0}"        # 1 = kein brew/npm install-Versuch
readonly SKIP_OBSIDIAN="${SKIP_OBSIDIAN:-0}"  # 1 = Obsidian.app nicht installieren

# ─── Preflight ──────────────────────────────────────────────────────────────

step "Preflight-Checks"

if [[ "$(uname)" != "Darwin" ]]; then
  error "Dieses Script ist aktuell nur für macOS getestet. Abbruch."
  exit 1
fi

# ─── Homebrew ───────────────────────────────────────────────────────────────

step "Homebrew"

if ! command -v brew >/dev/null 2>&1; then
  if [[ "$SKIP_DEPS" == "1" ]]; then
    warn "Homebrew fehlt und SKIP_DEPS=1 — skip Check"
  else
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
else
  ok "Homebrew: $(brew --version | head -1)"
fi

# ─── Git + gh CLI ───────────────────────────────────────────────────────────

step "Git und GitHub CLI"

for tool in git gh; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    if [[ "$SKIP_DEPS" == "1" ]]; then
      warn "$tool fehlt und SKIP_DEPS=1 — skip"
      continue
    fi
    info "Installiere $tool..."
    brew install "$tool"
  fi
  ok "$tool: $("$tool" --version | head -1)"
done

# GitHub-Auth prüfen
if ! gh auth status >/dev/null 2>&1; then
  warn "GitHub-CLI ist nicht authentifiziert."
  cat <<EOF

  ${C_YELLOW}Gleich startet der GitHub-Auth-Flow.${C_RESET}

  Antworte so:
    • Where do you use GitHub? → ${C_BLUE}GitHub.com${C_RESET}
    • Preferred protocol? → ${C_BLUE}HTTPS${C_RESET}
    • Authenticate Git with credentials? → ${C_BLUE}Yes${C_RESET}
    • How would you like to authenticate? → ${C_BLUE}Login with a web browser${C_RESET}

  ${C_YELLOW}⚠  WICHTIG:${C_RESET} gh zeigt dir gleich einen ${C_YELLOW}One-Time-Code${C_RESET}
  im Terminal an (Format: ${C_BLUE}XXXX-XXXX${C_RESET}). Notiere ihn, bevor
  du Enter drückst zum Browser-Öffnen. Im Browser musst du
  den Code eingeben.

EOF
  read -p "Bereit? Drücke Enter um den Auth-Flow zu starten..." _
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
  if [[ "$SKIP_DEPS" == "1" ]]; then
    warn "Node fehlt und SKIP_DEPS=1 — skip"
  else
    info "Installiere Node.js..."
    brew install node
    ok "Node: $(node --version)"
  fi
else
  ok "Node: $(node --version)"
fi

if ! command -v obsidian-cli >/dev/null 2>&1; then
  if [[ "$SKIP_DEPS" == "1" ]]; then
    warn "obsidian-cli fehlt und SKIP_DEPS=1 — skip"
  else
    info "Installiere obsidian-cli global (npm)..."

    # Fresh Macs: Homebrews Node-Prefix ist für User ohne sudo oft nicht
    # beschreibbar (/opt/homebrew/lib/node_modules → EACCES). Wenn das passiert,
    # setzen wir einen user-lokalen npm-prefix (~/.npm-global) und retryen.
    if ! npm install -g obsidian-cli 2>/dev/null; then
      warn "npm-global-Install fehlgeschlagen (Permission-Problem)."
      info "Konfiguriere user-lokalen npm-prefix unter ~/.npm-global..."
      mkdir -p "${HOME}/.npm-global"
      npm config set prefix "${HOME}/.npm-global"

      # PATH-Export zur Shell-Config (zsh/bash), falls noch nicht da
      SHELL_RC=""
      if [[ -n "${ZSH_VERSION:-}" ]] || [[ "${SHELL:-}" == */zsh ]]; then
        SHELL_RC="${HOME}/.zshrc"
      elif [[ -n "${BASH_VERSION:-}" ]] || [[ "${SHELL:-}" == */bash ]]; then
        SHELL_RC="${HOME}/.bashrc"
      fi
      if [[ -n "$SHELL_RC" ]]; then
        if [[ ! -f "$SHELL_RC" ]] || ! grep -q "\.npm-global/bin" "$SHELL_RC"; then
          {
            echo ""
            echo "# Added by install-team-setup.sh (Growth Nexus)"
            echo 'export PATH="$HOME/.npm-global/bin:$PATH"'
          } >> "$SHELL_RC"
          info "PATH-Export zu ${SHELL_RC} hinzugefügt (aktiv nach Terminal-Neustart)"
        fi
      fi
      export PATH="${HOME}/.npm-global/bin:${PATH}"

      info "Retry mit user-lokalem Pfad..."
      npm install -g obsidian-cli
    fi
    ok "obsidian-cli: installiert"
  fi
else
  ok "obsidian-cli: installiert"
fi

# ─── Obsidian.app ───────────────────────────────────────────────────────────

step "Obsidian"

if [[ ! -d "/Applications/Obsidian.app" ]]; then
  if [[ "$SKIP_OBSIDIAN" == "1" || "$SKIP_DEPS" == "1" ]]; then
    warn "Obsidian.app fehlt und SKIP gesetzt — skip"
  else
    info "Installiere Obsidian.app..."
    brew install --cask obsidian
    ok "Obsidian: /Applications/Obsidian.app vorhanden"
  fi
else
  ok "Obsidian: /Applications/Obsidian.app vorhanden"
fi

# ─── Python ─────────────────────────────────────────────────────────────────

step "Python"

if ! command -v python3 >/dev/null 2>&1; then
  if [[ "$SKIP_DEPS" == "1" ]]; then
    warn "Python fehlt und SKIP_DEPS=1 — skip"
  else
    info "Installiere Python..."
    brew install python3
    ok "Python: $(python3 --version)"
  fi
else
  ok "Python: $(python3 --version)"
fi

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

# growth-nexus
if [[ ! -d "${CONTEXT_DIR}/growth-nexus" ]]; then
  info "Klone ${REPO_GROWTH_NEXUS}..."
  cd "$CONTEXT_DIR"
  gh repo clone "$REPO_GROWTH_NEXUS"
  ok "growth-nexus geklont"
else
  info "growth-nexus existiert bereits, pulle..."
  cd "${CONTEXT_DIR}/growth-nexus" && git pull --ff-only || warn "Pull fehlgeschlagen, prüfe manuell"
  ok "growth-nexus aktualisiert"
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
  growth-nexus/                ← git-Repo, strategisch
  ryzon-context-vault/       ← git-Repo, operativ
  ├── ${USERNAME}/           ← DEIN Obsidian-Vault (öffne NUR diesen)
  └── shared/                ← Team-Scratchpad
  private/${USERNAME}/       ← NICHT git, nur lokal

${C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_GREEN}  Weiter geht's im Onboarding-Manual (~30 Min):${C_RESET}
${C_GREEN}  ${C_BLUE}https://ai-cockpit.ryzon.net/wissen/growth-nexus-onboarding${C_RESET}
${C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

Dort findest du:
  • Plugin-ZIP + Claude-Project-Instructions als Direkt-Downloads
  • Schritt-für-Schritt Cowork-Setup (Personal plugins · Connectors · Project)
  • Ersten /capture-Smoke-Test + Wochen-1-Ablauf

${C_YELLOW}Kurz-Version, falls du offline weitermachen willst:${C_RESET}

${C_BLUE}① Obsidian-Vault öffnen${C_RESET}
   Starte Obsidian.app und öffne den Folder:
   ${CONTEXT_DIR}/ryzon-context-vault/${USERNAME}
   ⚠  NUR deinen Folder ("${USERNAME}/"), NICHT den Repo-Root.

${C_BLUE}② Plugin in Cowork hochladen${C_RESET}
   Plugin-ZIP: https://ai-cockpit.ryzon.net/downloads/ryzon-knowledge-ops.zip
   Cowork → Customize → Personal plugins → "+" → Upload plugin → ZIP wählen → Toggle ON
   (Funktioniert NUR in Cowork, nicht im Web claude.ai)

${C_BLUE}③ Cowork-Project "Growth Nexus" erstellen${C_RESET}
   Instructions: https://ai-cockpit.ryzon.net/downloads/claude-project-instructions.md
   Connectors: Customize → Connectors → GitHub (beide Repos) + Drive
   Project-Location: ${CONTEXT_DIR}/ryzon-context-vault/${USERNAME}/

${C_YELLOW}Bei Problemen:${C_RESET} Simon direkt pingen.

EOF
