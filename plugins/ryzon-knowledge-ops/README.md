# ryzon-knowledge-ops

**Claude-Plugin für Ryzon Ops & Commercial — 9 Commands für strukturiertes Knowledge-Management: 5-Felder-Schema, Decision-Log, Quellen-Transparenz, Session-Summary, Validation-Workflow, F3 Consistency-Check, Archive-Search, Promotion-Flow.**

*v0.5.0 · Stand 2026-04-21 · Full Team-MVP (Woche-1-Scope komplett)*

---

## Was es macht

Neun Slash-Commands + drei Hintergrund-Agents für das Arbeiten mit einem 2-Repo-Knowledge-Setup (Obsidian operativ + growth-nexus strategisch):

### Commands

| Command | Zweck |
|---|---|
| **`/capture <type> <content>`** | Neuer Wissens-Eintrag (note · learning · analysis · meeting) mit 5-Dimensionen + Routing |
| **`/decision <question>`** | Business-Entscheidung strukturiert ins Decision-Log (Schema-Interview via Agent) |
| **`/pull <scope>`** | Relevanten Kontext laden — durchsucht User-Vault + shared/ + growth-nexus/ |
| **`/sources`** | Quellen der letzten Antwort detailliert + Trust-Level-Audit |
| **`/promote`** | Promotion-Kandidaten für Friday-Ritual vorbereiten (Cluster + Empfehlungen) |
| **`/distill`** | Session-Summary am Ende langer Chats — extrahiert Insights, bietet Speichern an |
| **`/validate <path>`** | Eintrag mit 3 Ratings validieren (Relevance · Accuracy · Completeness), auto-upgrade authority wenn alle ≥4 |
| **`/verify <question>`** | F3 Consistency-Check — 3 unabhängige Reasoning-Strategien (Direct, First-Principles, Contrarian), Konvergenz als Vertrauens-Signal |
| **`/find <query>`** | Suche im Knowledge-Archiv mit Metadaten-Filtern + Volltext + Scoring |

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

**Routing:** `maturity` × `sensitivity` bestimmt, wo ein Eintrag landet — eigener Vault, shared/, growth-nexus/, oder private/.

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

- **Zwei Repos:** `ryzon-context-vault` (operativ, individuelle Obsidian-Vaults + shared/) und `growth-nexus` (strategisch, kuratiert)
- **Privacy-Layer:** `~/Documents/projects/context/private/<person>/` außerhalb beider Repos (nie git-tracked)
- **Claude Project** als zentrales Interface, GitHub-Connector für beide Repos
- **Kein Custom MCP Server nötig** im Core-MVP — alles läuft über native Claude-App-Connectors

## Staged-Distribution (Ship-Strategie)

Alle 9 Commands sind in v0.5.0 gebaut. Simon kann wählen:

- **Option A — All-in:** v0.5.0 direkt am Install-Tag (Mo 27.04) distributieren. Sophie/Luca haben sofort den Full-Stack.
- **Option B — Staged:** Zurückhalten, schrittweise shippen (v0.2 Mo, v0.3 Di, v0.4 Mi, v0.5 Do). Gibt Sophie/Luca Zeit zu verdauen.

Empfehlung: **Option B für Erstes Rollout** (weniger Überforderung), **Option A für Mario-Onboarding ab Woche 3** (er bekommt den ausgereiften Stand).

## Was NICHT im v0.5.0

- `entity-linker`-Agent (nightly Wiki-Link-Enrichment) — Woche 2+
- Setup-Video (Screen-Recording) — Fr 01.05
- Slack-Integration — eigener Epic, post-MVP
- `public`-sensitivity — wenn Bedarf für investor-facing / Website-Content

## Entwicklung

Wichtigste Files:
- `.claude-plugin/plugin.json` — Plugin-Manifest (v0.5.0)
- `commands/*.md` — 9 Slash-Commands als Prompt-Files
- `agents/*.md` — 3 Background-Agents für Delegation
- `docs/frontmatter-schema.md` — Schema-Spec (single source of truth)

## Change Log

- **0.5.0 (2026-04-21):** Full Team-MVP — `/validate` (Insight-Rating mit Auto-Authority-Upgrade), `/verify` (F3 Consistency via Direct + First-Principles + Contrarian Reasoning), `/find` (Archive-Search mit Metadaten-Filter + Scoring)
- **0.2.0 (2026-04-21):** Team-MVP Core — 5-Felder-Schema, `sensitivity: self|team|pii`, Routing-Tabelle, 3 neue Agents (decision-facilitator, dimension-enricher, promotion-reviewer), 2 neue Commands (`/promote`, `/distill`), Commands refactored für Routing-Awareness
- **0.1.0 (2026-04-20):** Initialer MVP mit 4 Commands
