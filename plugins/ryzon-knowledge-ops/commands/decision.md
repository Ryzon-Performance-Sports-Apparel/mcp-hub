---
description: "Dokumentiere eine Business-Entscheidung strukturiert im Decision Log mit Begründung und Kontext-Referenzen"
---

Der User hat `/decision` aufgerufen. Arguments: $ARGUMENTS

Decisions sind **privilegierte Einträge** — sie gehen direkt nach `growth-nexus/decisions/` (strategisch) und haben strengeres Schema.

**Delegiere an den `decision-facilitator`-Agent** für das Interview.

## Dein Vorgehen (als decision-facilitator)

### 1. Verstehe die Frage

Der User nennt meist eine Frage oder ein Thema. Beispiel:
`/decision CRM-Tool-Wahl: HubSpot vs Pipedrive`

Extrahiere:
- **question** — die Entscheidungsfrage (aus $ARGUMENTS)
- **entities** — die betroffenen Dinge (CRM, HubSpot, Pipedrive)
- **domain** — aus Kontext (nachfragen wenn unklar)

### 2. Prüfe, ob bereits eine Decision existiert (Duplikat-Check)

**Bevor du eine neue Decision anlegst:**
1. Nutze GitHub-Connector, um im Pfad `growth-nexus/decisions/` zu suchen
2. Prüfe ob eine Decision zur selben Frage / zu denselben Entities existiert
3. Wenn ja: **zeige sie** und frage: *"Diese Decision existiert bereits. Ist die Situation neu (→ `supersedes`) oder war dir das nicht bewusst?"*
4. Bei `supersedes`: ID der alten Decision merken

### 3. Leite das Schema-Interview durch — eine Frage pro Turn

Frage den User in dieser Reihenfolge (**nie mehrere Fragen gleichzeitig**):

1. **"Welche Kontext-Quellen hast du für die Entscheidung genutzt?"**
   - User nennt Files, Quellen, KPIs → `context_used: [pfade]`
   - Wenn User nichts nennt: *"Keine Quellen? Reiner Bauchentscheid? → dann authority: draft statt approved."*

2. **"Wie lautet deine Entscheidung in einem Satz?"** → `decision: "..."`

3. **"Begründung — warum genau so?"** (mehrere Sätze ok) → `rationale: |` (multiline)

4. **"Wer hat mitentschieden?"** → `decided_by: [...]`

5. **"Supersedes eine frühere Decision?"** (nur falls Schritt 2 eine fand)
   → `supersedes: <id>`

### 4. Die 5 Dimensionen automatisch setzen (Decision-Defaults)

- `type: decision`
- `maturity: strategic`
- `authority: approved` (wenn `context_used` gefüllt) oder `draft` (wenn nicht)
- `sensitivity: team` (default · Override zu `pii` wenn es um Personalthemen / HR geht)
- `source: manual`
- `lifespan: durable`

### 5. ID + Filename generieren

- `id: dec-<YYYY-MM-DD>-<slug>`
- filename: `<id>.md`
- pfad: `growth-nexus/decisions/<id>.md`

### 6. Body generieren

```markdown
---
type: decision
id: dec-2026-04-21-crm-tool
domain: ops
author: simon
date: 2026-04-21
maturity: strategic
authority: approved
sensitivity: team
source: manual
lifespan: durable
decided_at: 2026-04-21
decided_by: [simon, mario]
context_used:
  - growth-nexus/analyses/2026-04-15-crm-kpi-analysis.md
  - growth-nexus/meetings/2026-04-12-ops-tooling-review.md
question: "Welches CRM setzen wir ab Q2 ein?"
decision: "HubSpot"
rationale: |
  [User's Begründung als mehrzeiliger Text]
entities: [crm, hubspot, pipedrive]
tags: [crm, tooling, q2-planning]
---

# CRM-Tool-Wahl: HubSpot vs Pipedrive

## Frage
[question]

## Entscheidung
[decision]

## Begründung
[rationale als lesbare Prosa]

## Was wir berücksichtigt haben
- [Quelle 1 mit 1-Zeilen-Kern]
- [Quelle 2 mit 1-Zeilen-Kern]

## Was sich ändern müsste, um die Decision zu überdenken
[1–2 Bedingungen — macht spätere Reviews greifbar]
```

### 7. Commit nach growth-nexus

- Pfad: `growth-nexus/decisions/<id>.md`
- Commit-Message: `decision(<domain>): <question>`
- Push automatisch (nach User-Bestätigung)

### 8. Bestätigen + Verweise

Antworte: *"Decision als `<id>` im Log. Sie wird ab jetzt bei ähnlichen Fragen automatisch herangezogen (`authority: approved`, `weight: high`). Willst du das jetzt an Sophie/Luca teilen?"*

## Wichtig

- **Keine Decision ohne rationale** — das ist der Kern des ganzen Logs
- **Wenn User ohne Kontext-Quellen entscheidet:** sage explizit *"Wir markieren das als authority: draft — beim nächsten Review prüfen wir, ob sie approved werden kann."*
- **Niemals eine Decision überschreiben** — immer `supersedes` nutzen, alte bleibt erhalten
- **Meta-Zeile am Ende, falls Schema-Lücken:** z.B. *"📝 Feld 'impact' fehlt — wäre hilfreich für post-hoc Evaluierung"*
- **Bei Personalthemen / HR:** `sensitivity: pii` → landet in `private/<author>/strategic/` statt `growth-nexus/decisions/`
