# Simon-Tasks · Pre-Rollout bis Launch

*Persönliche Execution-Checkliste · Dependency-geordnet · Checkbox-basiert*

---

## 🔄 Update 2026-04-22 (v1.1) — aktueller Stand

**Erledigt / Automatisiert:**
- [x] Bug-Fix-Script gebaut + auf Granola angewendet ✓
- [x] Area-Tagger-Agent Bug gefixt + gepusht (ai-context commit) ✓
- [x] Plugin v0.5.0 komplett — capture/decision/pull/sources/promote/distill/validate/verify/find ✓
- [x] Install-Script + Sandbox-Test-Mode ✓
- [x] `ryzon-context-vault` Repo live auf GitHub ✓
- [x] `growth-nexus` Repo live auf GitHub (ersetzt ai-context als Team-Strategie-Repo) ✓

**Strategie-Repo umbenannt:** `ai-context` → `growth-nexus` (clean slate). Simons `ai-context` bleibt sein Solo-Sandbox, Team arbeitet mit `growth-nexus`. Kein Curation-Pass über ai-context mehr nötig — growth-nexus startet leer.

**Noch zu tun bis Launch:**
- [ ] Install-Script auf Test-User laufen lassen (30 Min) · siehe scripts/README.md Testing-Sektion
- [ ] Plugin-ZIP bauen + selbst in Claude App uploaden und dogfooden
- [ ] Setup-Video aufnehmen (2 h, Freitag 01.05)
- [ ] Sophie + Luca als GitHub-Collaborators zu `growth-nexus` und `ryzon-context-vault` einladen
- [ ] Kalender-Invites: Mo 27.04 Install · Mi 29.04 Check-in · Fr 09.05 1. Retro

Die Tasks unten sind **historisch** (v1.0, vor dem growth-nexus-Rename). Nützlich als Hintergrund, aber nicht mehr aktiv abzuarbeiten.

---

## Tag 1 · Mi 22.04 · Bug-Fix & Repo-Foundation (~5 h) [HISTORISCH]

### T1 — Bug-Fix-Script bauen & laufen lassen
- [ ] Script `/Users/simonheinken/Documents/projects/mcp/scripts/fix-double-tags.py` erstellen
- [ ] Logik: YAML-frontmatter parsen, beide `tags`-Arrays mergen + deduplizieren, zurückschreiben
- [ ] Trocken-Run auf 3 Test-Files unter `/projects/context/context-vault/Granola/`
- [ ] Full-Run auf `/projects/context/growth-nexus/` + `/projects/context/context-vault/Granola/`
- [ ] **Done**: `grep -c "^tags:" <file>` ≤ 1 für alle betroffenen Files
- [ ] Commit: `fix: deduplicate tags frontmatter in granola and ai-context`
- **Aufwand:** 1 h

### T2 — Area-Tagger-Agent-Bug fixen
- [ ] Path: `/Users/simonheinken/Documents/projects/context/growth-nexus/claude-code/agents/meeting-notes/area-tagger-agent.md`
- [ ] Logik ändern: bestehenden `tags:`-Array lesen, neue Tags mergen, ALS EINEN Array zurückschreiben
- [ ] Test: Agent laufen lassen auf 2 neuen Granola-Files, dann `grep` check
- [ ] **Done**: keine neuen Duplikate entstehen
- [ ] Commit: `fix(area-tagger): merge tags array instead of append`
- **Aufwand:** 30 min

### T3 — Curation-Pass über bestehende Granola-Notes
- [ ] `/projects/context/context-vault/Granola/` (108 Files) sichten
- [ ] Kategorisieren in: **team-shareable** (bleibt) · **private** (verschieben nach `growth-nexus/private/simon/`) · **delete**
- [ ] Private: 1on1-Notizen mit Luca/Sophie, Gesundheits-Themen, HR-Themen
- [ ] **Done**: keine private-Inhalte mehr in `context-vault/Granola/` nach diesem Pass
- [ ] Commit in ai-context: `chore: move private notes out of team-shared path`
- **Aufwand:** 2–3 h (das ist der größte Brocken heute)

### T4 — `growth-nexus` Struktur erweitern
- [ ] Neue Folders: `growth-nexus/private/{simon,sophie,luca}/` · `growth-nexus/decisions/` · `growth-nexus/schema/`
- [ ] `.gitignore` updaten:
  ```
  private/
  .DS_Store
  *.pptx
  *.html
  **/*.tmp
  ```
- [ ] `README.md` in `private/` mit Warnung: *"This folder is .gitignored. NEVER commit files here to shared branches."*
- [ ] **Done**: `git ls-files growth-nexus/private/` ist leer
- [ ] Commit: `feat: add team-ready folder structure with private layer`
- **Aufwand:** 30 min

### T5 — Neues Repo `ryzon-context-vault` anlegen
- [ ] GitHub: `gh repo create Ryzon-Performance-Sports-Apparel/ryzon-context-vault --private`
- [ ] Lokal: `mkdir ~/Documents/projects/context/ryzon-context-vault && cd $_ && git init`
- [ ] Folder-Struktur: `simon/`, `sophie/`, `luca/`, `shared/`, `granola/`
- [ ] `.obsidian/`-Config anlegen (kopieren aus `context-vault/.obsidian/` als Basis, Theme etc. sauber)
- [ ] `.gitignore`:
  ```
  .obsidian/workspace
  .obsidian/workspace.json
  .obsidian/workspaces.json
  .DS_Store
  .trash/
  *.tmp
  ```
- [ ] `README.md`: was ist der Vault, Folder-Konventionen, wie öffnen in Obsidian
- [ ] Initial Commit + Push
- [ ] Sophie + Luca als Collaborators einladen
- [ ] **Done**: Repo auf GitHub sichtbar, Obsidian öffnet den Vault ohne Fehler
- **Aufwand:** 1 h

---

## Tag 2 · Do 23.04 · Schema & Plugin-Agents (~7 h)

### T6 — Schema mit 5 MVP-Dimensionen finalisieren
- [ ] Update: `/Users/simonheinken/Documents/projects/mcp/plugins/ryzon-knowledge-ops/docs/frontmatter-schema.md`
- [ ] 5 Dimensionen: `maturity`, `authority`, `sensitivity`, `source`, `lifespan`
- [ ] Type-spezifische Defaults dokumentieren:
  - note → operational · draft · team · manual · ephemeral
  - meeting → operational · draft · team · manual · ephemeral
  - learning → operational · draft · team · manual · ephemeral
  - analysis → strategic · draft · team · derived · durable
  - decision → strategic · approved · team · manual · durable
- [ ] Copy ins `growth-nexus/schema/frontmatter.md` (single source of truth für Agents)
- [ ] **Done**: Schema-Doc 100% konsistent zwischen mcp-Repo und ai-context
- **Aufwand:** 1 h

### T7 — Plugin-Commands auf 5-Felder-Schema updaten
- [ ] `plugins/ryzon-knowledge-ops/commands/capture.md` → Agent-Delegation an `dimension-enricher`
- [ ] `plugins/ryzon-knowledge-ops/commands/decision.md` → Agent-Delegation an `decision-facilitator`
- [ ] `plugins/ryzon-knowledge-ops/commands/pull.md` → Filter-Logik auf neue Felder (`maturity`, `authority`)
- [ ] `plugins/ryzon-knowledge-ops/commands/sources.md` → Trust-Level im Output
- [ ] `plugin.json` Version bump: `0.1.0` → `0.2.0`
- [ ] **Done**: alle Commands referenzieren die 5 Dimensionen und delegieren sinnvoll
- **Aufwand:** 1–2 h

### T8 — Agent `dimension-enricher` bauen
- [ ] Path: `plugins/ryzon-knowledge-ops/agents/dimension-enricher.md`
- [ ] Input: frisch erstelltes `.md`-File (aus `/capture`)
- [ ] Output: Frontmatter mit 5 Dimensionen gesetzt (Defaults aus Type + Override aus User-Signals)
- [ ] Scoring-Logik teilweise aus `area-tagger-agent` übernehmen (confidence, signals)
- [ ] Test: 3 Example-Files mit verschiedenen Types → alle 5 Felder korrekt gesetzt
- [ ] **Done**: Agent-Test zeigt 100% Schema-Compliance auf 5 Files
- **Aufwand:** 2 h

### T9 — Agent `decision-facilitator` bauen
- [ ] Path: `plugins/ryzon-knowledge-ops/agents/decision-facilitator.md`
- [ ] Verhalten:
  1. User-Frage parsen
  2. Duplicate-Check gegen `growth-nexus/decisions/` (ist Decision bereits da?)
  3. Schema-Interview durchlaufen (context_used, rationale, decided_by, supersedes)
  4. File in `growth-nexus/decisions/dec-YYYY-MM-DD-slug.md` schreiben
- [ ] Test: `/decision CRM-Tool-Wahl` → vollständiges Schema, kein Duplikat mit bestehender
- [ ] **Done**: Beispiel-Decision wird sauber geschrieben, Duplicate-Check funktioniert
- **Aufwand:** 2 h

### T10 — Claude Project Instructions finalisieren
- [ ] Update: `docs/knowledge-setup/claude-project-instructions-template.md`
- [ ] 5-Dimensionen-Awareness einbauen
- [ ] Trust-Level-Regel (verified first, draft kennzeichnen)
- [ ] Decision-Log-Privileg (immer auf `weight: high` matchen bei recurring questions)
- [ ] Quellen-Block (F4) bestätigen
- [ ] Das sind die Instructions die Sophie/Luca in ihr Claude Project kopieren
- [ ] **Done**: Template 1:1 copy-paste-fähig für Claude App
- **Aufwand:** 1 h

### T11 — Team-README für Sophie/Luca
- [ ] Path: `docs/knowledge-setup/team-readme.md`
- [ ] Sektionen: 
  - Was ist das Setup (1 Absatz + Link auf Diagram-Doc)
  - Install-Steps (Referenz auf install-script)
  - Die 4 Commands mit Mini-Beispielen
  - FAQ: häufige Stolperstellen
  - Wo melde ich Bugs (Slack-Channel)
- [ ] **Done**: README beantwortet "wie nutze ich das?" in <10 Min Lesezeit
- **Aufwand:** 1 h

---

## Tag 3 · Fr 24.04 · Install-Script & Puffer (~4 h)

### T12 — Install-Script bauen
- [ ] Path: `/Users/simonheinken/Documents/projects/mcp/scripts/install-team-setup.sh`
- [ ] Steps gemäß Plan §1.5 (check deps, install Obsidian + obsidian-cli, clone repos, configure)
- [ ] Shebang + `set -euo pipefail` + klare Error-Messages
- [ ] `README.md` nebendran mit Walkthrough + manuellen Steps
- [ ] Test: auf Test-Mac (z.B. eigene VM oder sauberer User) laufen lassen
- [ ] **Done**: Script läuft durch ohne Intervention, Output dokumentiert was manuell fehlt (Claude App Plugin Upload, Project-Setup)
- **Aufwand:** 3 h

### T13 — Plugin-ZIP bauen
- [ ] `cd plugins/ && zip -r ryzon-knowledge-ops.zip ryzon-knowledge-ops/ -x "*.DS_Store"`
- [ ] Verifizieren: ZIP enthält `.claude-plugin/`, `commands/`, `agents/`, `docs/`, `README.md`
- [ ] In Claude App testweise selbst uploaden + einmal `/capture` durchspielen
- [ ] **Done**: Plugin zeigt im Claude App Directory alle 4 Commands
- **Aufwand:** 30 min

### T14 — Puffer + letzte Checks
- [ ] Alle Commits auf `docs/meeting-visual-and-plugin` oder neuem Launch-Branch pushen
- [ ] PR mergen in main
- [ ] Kalender-Invites für Mo 27.04 Install-Sessions rausschicken (30 Min Sophie, 30 Min Luca)
- [ ] Slack-Channel `#knowledge-ops-experiment` anlegen
- [ ] Kalender-Serie "Friday-Retro" ab Fr 08.05 14:00–14:45
- **Aufwand:** 30 min

---

## Launch-Day · Mo 27.04

### T15 — Install-Session Sophie (30 Min)
- [ ] Screen-Share starten
- [ ] Install-Script zusammen durchlaufen
- [ ] Claude Project erstellen: "Ryzon Knowledge Ops"
- [ ] Plugin uploaden, GitHub + Drive Connector konfigurieren
- [ ] Instructions aus Template einfügen
- [ ] Live: erstes `/capture learning ...` + `/decision ...`
- [ ] Slack-Channel zeigen, erste Fragen einsammeln

### T16 — Install-Session Luca (30 Min)
- [ ] Selber Flow wie bei Sophie
- [ ] Besondere Sorgfalt bei Trust/Transparenz-Themen (Luca's Skepsis)
- [ ] Ihm den Quellen-Audit-Block live demonstrieren

### T17 — Dienstagsmorgen 28.04: Offizieller Start
- [ ] Kick-off-Nachricht im Slack-Channel
- [ ] Ich mache den ersten `/capture` um den Flow zu bootstrappen
- [ ] Mid-Week-Check-In Mi 29.04 bestätigen

---

## Post-Launch (nicht blocking)

### T18 — Vor 1. Friday-Retro (Fr 08.05)
- [ ] Agent `promotion-reviewer` bauen (2 h)
- [ ] Command `/promote` bauen (1 h)
- [ ] Friday-Retro-Template erstellen (30 min)
- [ ] Testlauf: `/promote` auf 2 Example-Files von mir selbst

### T19 — Woche 2
- [ ] Agent `entity-linker` bauen + nightly schedulen (3 h)
- [ ] Obsidian-CLI in Install-Script integrieren
- [ ] Feedback aus Woche 1 verarbeiten

---

## Running-Total Aufwand

| Phase | Stunden |
|---|---|
| Tag 1 (Mi) | 5 |
| Tag 2 (Do) | 7 |
| Tag 3 (Fr) | 4 |
| Launch-Day (Mo) | 2 |
| **Bis zum Launch** | **~18 h** |
| Post-Launch Woche 1 | ~3.5 h |
| Post-Launch Woche 2 | ~3 h |

---

## Wenn etwas schiefgeht

- **T1/T2 länger als 1h** → area-tagger komplett rebuilden, nicht patchen
- **T3 länger als 3h** → nur offensichtlich private Files verschieben, Rest belassen, beim 1. Retro nachziehen
- **T8/T9 agent-Logik unklar** → dokumentiere Edge Cases, ship mit conservative Defaults, verfeinere basierend auf Feedback
- **T12 Install-Script-Probleme auf Sophie/Luca's Maschine** → fallback auf manuelle Install-Steps aus README, Script iterieren

## Pro-Tipp

Am Ende jedes Tages den Plan-Fortschritt im Status-Doc (`2026-04-20-status-synthese.md`) kurz updaten, damit du morgen den Faden schnell aufnehmen kannst.
