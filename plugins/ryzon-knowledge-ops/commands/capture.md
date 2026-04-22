---
description: "Lege einen strukturierten Wissens-Eintrag (note/learning/analysis/meeting) im passenden Folder an"
---

Der User hat `/capture` aufgerufen. Arguments: $ARGUMENTS

## Dein Vorgehen

### 1. Parse Arguments

Der erste Token ist der **type**, der Rest ist der **content**.

Erlaubte types: `note` · `learning` · `analysis` · `meeting`

Beispiel: `/capture learning Apollo bevorzugt Video-Content über Single-Image, CTR 2x höher`
→ type=learning, content="Apollo bevorzugt..."

**Wenn type fehlt oder ungültig:** frage nach mit Multi-Choice: *"Welcher Typ — note, learning, analysis, oder meeting?"*

### 2. Defaults setzen (delegiert an dimension-enricher)

Delegiere an den **`dimension-enricher`**-Agent (oder setze selbst) die 5 Dimensionen basierend auf type:

| type | maturity | authority | sensitivity | source | lifespan |
|---|---|---|---|---|---|
| note | operational | draft | self | manual | ephemeral |
| learning | operational | draft | self | manual | ephemeral |
| meeting | operational | draft | team | manual | ephemeral |
| analysis | strategic | draft | team | derived | durable |

Frage den User nur, wenn eine Dimension vom Default abweichen soll. Signal-Wörter im content:
- *"für das Team"*, *"alle sollten wissen"* → `sensitivity: team`
- *"ist verified"*, *"validiert"*, *"beschlossen"* → `authority: approved`
- *"privat"*, *"nicht teilen"*, *"intern"*, Personennamen in 1on1-Kontext → `sensitivity: pii`
- *"wichtig langfristig"*, *"Standard"* → `lifespan: durable`

### 3. Pflichtfelder ergänzen

Schema (siehe `plugins/ryzon-knowledge-ops/docs/frontmatter-schema.md`):

- `type` — aus Args
- `date` — heutiges Datum (ISO)
- `author` — aktueller User (einmal pro Session fragen: *"Wer bist du? (simon/sophie/luca/mario)"*)
- `domain` — sales · marketing · product · ops · customer · engineering · finance
  - Aus content ableiten · bei Mehrdeutigkeit nachfragen
- `entities` — Kunden, Projekte, Kampagnen
  - Extrahiere aus content, schlage 2–3 vor, lass User bestätigen
- `tags` — 2–5 Tags aus README-Taxonomie
  - Wenn kein passender Tag existiert, neuen vorschlagen und am Ende der Antwort unter **📝 Meta:** für Retro flaggen

### 4. Routing bestimmen — WO das File landet

Basierend auf `maturity` × `sensitivity`:

| maturity | sensitivity | Landeplatz |
|---|---|---|
| operational | self | `ryzon-context-vault/<author>/<type>s/<filename>` |
| operational | team | `ryzon-context-vault/shared/<type>s/<filename>` |
| operational | pii | `~/Documents/projects/context/private/<author>/<filename>` (lokal, nicht git) |
| strategic | team | `growth-nexus/<domain-or-type-path>/<filename>` (via promote, NICHT direkt) |
| strategic | pii | `~/Documents/projects/context/private/<author>/strategic/<filename>` |

**Wichtig:** `strategic + team` landet NICHT direkt in `growth-nexus/` beim `/capture` — das ist Promotion-Territory (Friday-Ritual). Setze stattdessen `maturity: operational` initial und promovier später. Falls User explizit will: warne kurz, dann erlaube.

### 5. Filename generieren

Format: `<YYYY-MM-DD>-<type>-<slug>.md`
- `slug` = 4–6 bedeutsame Wörter des content, lowercase-kebab
- Beispiel: `2026-04-21-learning-apollo-video-content-performance.md`

### 6. File schreiben

Nutze den **GitHub-Connector** für operationale commits in `ryzon-context-vault` oder lokalen Write für `private/`.

Commit-Message: `capture(<author>): <title>` für committed Files.

Für `private/` → kein Commit, nur File-Write.

### 7. Body strukturiert generieren

```markdown
---
type: learning
date: 2026-04-21
author: sophie
maturity: operational
authority: draft
sensitivity: self
source: manual
lifespan: ephemeral
domain: marketing
entities: [apollo, video-content]
tags: [performance, creative]
---

# Apollo: Video-Content performt 2x besser

[Kondensierter Content, 100–200 Wörter — NICHT copy-paste vom User,
sondern knapp redigiert. Fragen am Ende falls offen.]
```

### 8. Bestätigen

Antworte: *"Gespeichert als `<pfad>`. Dimensionen: maturity=operational · authority=draft · sensitivity=self. Willst du etwas anpassen?"*

Lass den User die Chance, Dimensionen zu overriden oder Tags nachzubearbeiten.

## Wichtig

- **Keine Einträge ohne Pflichtfelder** — lieber 1–2 Rückfragen als ein unvollständiger Eintrag
- **Kondensiere den Content** — User schreibt oft wie gesprochen, dein Job ist Struktur
- **Default authority: draft** — Upgrade auf `approved` ist bewusster Akt (via `/validate` oder explicit)
- **Bei sensitivity: pii** — niemals nach `shared/` oder `growth-nexus/` schreiben, IMMER `private/`
- **Bei strategic** — nicht direkt nach `growth-nexus/` beim /capture, das passiert via `/promote` im Friday-Ritual
