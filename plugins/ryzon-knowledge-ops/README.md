# ryzon-knowledge-ops

**Claude-Plugin für Ryzon Ops & Commercial — strukturierte Wissens-Erfassung mit 5-Felder-Schema, Decision Log, transparente Retrieval, Session-Summary, Promotion-Flow.**

*v0.2.0 · Stand 2026-04-21 · Team-MVP Core*

---

## Was es macht

Sechs Slash-Commands + drei Hintergrund-Agents für das Arbeiten mit einem 2-Repo-Knowledge-Setup (Obsidian operativ + ai-context strategisch):

### Commands

| Command | Zweck |
|---|---|
| **`/capture <type> <content>`** | Neuer Wissens-Eintrag (note · learning · analysis · meeting) mit 5-Dimensionen + Routing |
| **`/decision <question>`** | Business-Entscheidung strukturiert ins Decision-Log (Schema-Interview via Agent) |
| **`/pull <scope>`** | Relevanten Kontext laden — durchsucht User-Vault + shared/ + ai-context/ |
| **`/sources`** | Quellen der letzten Antwort detailliert + Trust-Level-Audit |
| **`/promote`** | Promotion-Kandidaten für Friday-Ritual vorbereiten (Cluster + Empfehlungen) |
| **`/distill`** | Session-Summary am Ende langer Chats — extrahiert Insights, bietet Speichern an |

### Agents (Hintergrund, delegiert von Commands)

| Agent | Zweck |
|---|---|
| `decision-facilitator` | Treibt das /decision Schema-Interview, prüft Duplikat-Check |
| `dimension-enricher` | Setzt 5-Dimensionen-Defaults basierend auf type + content-signals |
| `promotion-reviewer` | Clustert operative Einträge der Woche, Empfehlungen für Promotion |

### 5-Felder-Schema (das Herzstück)

Jeder Eintrag trägt diese 5 Dimensionen (siehe `docs/frontmatter-schema.md`):

| Dimension | Werte |
|---|---|
| `maturity` | operational · strategic |
| `authority` | draft · approved · official |
| `sensitivity` | self · team · pii |
| `source` | manual · derived · system |
| `lifespan` | ephemeral · durable |

**Routing:** `maturity` × `sensitivity` bestimmt, wo ein Eintrag landet — eigener Vault, shared/, ai-context/, oder private/.

## Installation

### Für den Endnutzer (Sophie, Luca, Mario)

1. Claude App öffnen
2. **Customize** → **Directory** → **Plugins** → **Personal**
3. **Upload plugin** → dieses Verzeichnis als ZIP hochladen
4. Plugin aktivieren im Claude Project "Ryzon Knowledge Ops"
5. Erste Nutzung: `/pull sales` oder `/capture note ...`

### Für den Admin (Simon)

Distribution-Optionen:
- **Direct Upload:** ZIP dieses Verzeichnisses in Claude App hochladen (Personal Plugin)
- **Marketplace:** eigene Ryzon-Plugin-Marketplace auf **privatem** GitHub hosten, im Directory via "Add marketplace" einbinden

## Architektur-Annahmen

- **Zwei Repos:** `ryzon-context-vault` (operativ, individuelle Obsidian-Vaults + shared/) und `ai-context` (strategisch, kuratiert)
- **Privacy-Layer:** `~/Documents/projects/context/private/<person>/` außerhalb beider Repos (nie git-tracked)
- **Claude Project** als zentrales Interface, GitHub-Connector für beide Repos
- **Kein Custom MCP Server nötig** im Core-MVP — alles läuft über native Claude-App-Connectors

## Was NICHT im v0.2.0

- `/validate` — Insight-Rating Command (shipt v0.3.0, Di 28.04)
- `/verify` — F3 Consistency-Check (shipt v0.4.0, Mi 29.04)
- `/find` — Chat-Archive-Browsing (shipt v0.5.0, Do 30.04)
- `entity-linker`-Agent (nightly Wiki-Links) — Woche 2+
- Slack-Integration — eigener Epic

## Entwicklung

Wichtigste Files:
- `.claude-plugin/plugin.json` — Plugin-Manifest
- `commands/*.md` — 6 Slash-Commands als Prompt-Files
- `agents/*.md` — 3 Background-Agents für Delegation
- `docs/frontmatter-schema.md` — Schema-Spec (single source of truth)

## Change Log

- **0.2.0 (2026-04-21):** Team-MVP Core — 5-Felder-Schema, `sensitivity: self|team|pii`, Routing-Tabelle, 3 neue Agents (decision-facilitator, dimension-enricher, promotion-reviewer), 2 neue Commands (`/promote`, `/distill`), Commands refactored für Routing-Awareness
- **0.1.0 (2026-04-20):** Initialer MVP mit 4 Commands
