# Frontmatter-Schema für Knowledge-Einträge

*v1.1 · 5-Felder-MVP · 2026-04-21*

Jede `.md`-Datei im Vault oder in `growth-nexus/` trägt YAML-Frontmatter mit den folgenden Feldern. Die **5 MVP-Dimensionen** sind das Herzstück — sie bestimmen wo ein Eintrag landet, wie Claude ihn behandelt und wer Zugriff hat.

---

## Pflichtfelder

### Kern-Identifikation

| Feld | Typ | Werte | Beispiel |
|---|---|---|---|
| `type` | enum | `note` \| `meeting` \| `learning` \| `analysis` \| `decision` | `learning` |
| `date` | ISO-Date | YYYY-MM-DD | `2026-04-21` |
| `author` | enum | `sophie` \| `luca` \| `simon` \| `mario` | `sophie` |

### Die 5 MVP-Dimensionen

| Feld | Werte | Bedeutung | Wirkt auf |
|---|---|---|---|
| `maturity` | `operational` \| `strategic` | Reifegrad — wo im Kurations-Flow | Claude priorisiert `strategic` bei Team-Standard-Fragen |
| `authority` | `draft` \| `approved` \| `official` | Verbindlichkeit | Claude kennzeichnet `draft` in Antworten · `official` ist gesetzt |
| `sensitivity` | `self` \| `team` \| `pii` | Sichtbarkeits-Scope | Steuert Landeplatz (siehe Routing-Tabelle unten) |
| `source` | `manual` \| `derived` \| `system` | Wer/was hat's erstellt | Transparenz: Mensch vs. Agent vs. System |
| `lifespan` | `ephemeral` \| `durable` | Langlebigkeit | `ephemeral` wird nach ~90 Tagen archiviert · `durable` bleibt |

### Domain-Context

| Feld | Typ | Werte | Beispiel |
|---|---|---|---|
| `domain` | enum | `sales` \| `marketing` \| `product` \| `ops` \| `customer` \| `engineering` \| `finance` | `sales` |
| `entities` | array | Kunden, Projekte, Kampagnen (lowercase-kebab) | `[apollo, q2-campaign]` |
| `tags` | array | 2–5 Tags (siehe Taxonomie) | `[performance, creative]` |

---

## Routing-Tabelle — Wo landet ein Eintrag?

Basierend auf `maturity` × `sensitivity`:

| maturity | sensitivity | Landeplatz | Git-Status |
|---|---|---|---|
| operational | self | `ryzon-context-vault/<person>/…` (eigener Obsidian-Vault) | committed |
| operational | team | `ryzon-context-vault/shared/…` (Team-Scratchpad) | committed |
| operational | pii | `~/Documents/projects/context/private/<person>/…` | **nicht git** |
| strategic | team | `growth-nexus/…` (nach Promotion via Friday-Ritual) | committed |
| strategic | pii | `private/<person>/strategic/…` | **nicht git** |

**Hinweis:** `sensitivity: pii` bedeutet **immer** → `private/`-Folder außerhalb beider Repos. `self` bleibt im eigenen Vault (lokal committed, für Team lesbar via git pull, aber Obsidian öffnet nur eigene). `team` explizit für Zusammenarbeit.

---

## Defaults pro Type

Der `dimension-enricher`-Agent setzt diese Defaults. User können überschreiben.

| `type` | maturity | authority | sensitivity | source | lifespan | Landet in |
|---|---|---|---|---|---|---|
| `note` | operational | draft | self | manual | ephemeral | eigener Vault |
| `learning` | operational | draft | self | manual | ephemeral | eigener Vault |
| `meeting` | operational | draft | team | manual | ephemeral | `shared/` |
| `analysis` | strategic | draft | team | derived | durable | `growth-nexus/` (via promote) |
| `decision` | strategic | approved | team | manual | durable | `growth-nexus/decisions/` |

---

## Zusätzliche Pflichtfelder für `type: decision`

| Feld | Typ | Pflicht | Beispiel |
|---|---|---|---|
| `id` | string | ja | `dec-2026-04-21-crm-tool` |
| `question` | string | ja | `"Welches CRM setzen wir ab Q2 ein?"` |
| `decision` | string | ja | `"HubSpot"` |
| `rationale` | string (multiline) | ja | `"..."` |
| `decided_by` | array | ja | `[simon, mario]` |
| `decided_at` | ISO-Date | ja | `2026-04-21` |
| `context_used` | array (paths) | empfohlen | `[growth-nexus/meetings/...]` |
| `supersedes` | string (id) | optional | `dec-2025-11-02-crm-eval` |

---

## Optionale Validation-Felder (ab `/validate` Command, v0.3.0)

Wenn User via `/validate` einen Eintrag ratet, wird folgendes Objekt hinzugefügt:

```yaml
validation:
  relevance: 5        # 1-5
  accuracy: 4         # 1-5
  completeness: 3     # 1-5
  validated_by: sophie
  validated_at: 2026-04-22
```

Regel: wenn alle drei Ratings ≥ 4 → `authority: approved` wird automatisch gesetzt.

---

## Tag-Taxonomie v0.1

Tags dürfen aus dieser Liste gewählt werden. Neue Tags → im Retro besprechen, nicht freihändig einführen.

### Funktionale Tags
- `performance` — Zahlen, KPIs, ROAS, Conversion
- `creative` — Ads, Visuals, Copy
- `process` — Prozesse, Workflows, Abläufe
- `tooling` — Software-Entscheidungen, Stacks
- `customer` — direkte Kunden-Insights

### Zeitliche Tags
- `q1-planning`, `q2-planning`, `q3-planning`, `q4-planning`
- `bfcm` — Black-Friday / Cyber-Monday
- `season-spring`, `season-summer`, etc.

### Thematische Tags
- `pricing` — Preisentscheidungen, -analysen
- `launch` — Produkt-Launches
- `crm`, `hubspot`, `pipedrive`
- `apollo`, `keyaccount-<name>`

### Meta-Tags
- `needs-review` — geflaggt für Retro
- `contested` — mehrere Leute haben verschiedene Meinungen
- `hypothesis` — These, nicht verifiziert

---

## File-Naming-Convention

### Pfad-Struktur

```
ryzon-context-vault/                    (operativ)
├── <person>/                           eigener Vault (self + operational)
│   ├── notes/
│   ├── learnings/
│   ├── granola/                        auto-synced Meetings
│   └── analyses/                       persönliche Analysen
└── shared/                             (team + operational)
    ├── meetings/                       Meeting-Protokolle
    ├── scratchpad/                     Team-Draft-Space
    └── drafts/                         collab-Entwürfe

growth-nexus/                             (strategisch)
├── meetings/                           promoviert
├── decisions/                          Decision-Log
├── domain/<area>/                      Team-Standards
└── analyses/                           validierte Analysen

~/Documents/projects/context/private/   (lokal only, nicht git)
└── <person>/
    ├── 1on1/
    ├── hr/
    └── strategic/                      pii + strategisch
```

### Dateiname

Format: `<YYYY-MM-DD>-<type>-<slug>.md`

Beispiele:
- `ryzon-context-vault/sophie/learnings/2026-04-21-learning-apollo-video-performance.md`
- `growth-nexus/decisions/dec-2026-04-21-crm-tool.md`
- `ryzon-context-vault/shared/meetings/2026-04-21-meeting-q2-planning.md`

Für Decisions: Dateiname = `<id>.md`

---

## Beispiel: Learning von Sophie (self, operational)

```markdown
---
type: learning
domain: marketing
author: sophie
date: 2026-04-21
# 5 Dimensionen
maturity: operational
authority: draft
sensitivity: self
source: manual
lifespan: ephemeral
# Domain-Context
entities: [apollo, video-content]
tags: [performance, creative]
---

# Apollo: Video-Content performt 2x besser als Single-Image

Im Review vom 18.04. zeigte sich deutlich: Apollos Video-Ads erzielten
im März 2.0x CTR im Vergleich zu Single-Image-Ads bei vergleichbarem Spend.

Zu prüfen: ob das über weitere Kunden konsistent ist oder Apollo-spezifisch.
```

→ Landet in: `ryzon-context-vault/sophie/learnings/2026-04-21-learning-apollo-video.md`

---

## Beispiel: Decision (team, strategic)

```markdown
---
type: decision
id: dec-2026-04-21-crm-tool
domain: ops
author: simon
date: 2026-04-21
# 5 Dimensionen (Decision-Defaults)
maturity: strategic
authority: approved
sensitivity: team
source: manual
lifespan: durable
# Decision-spezifisch
decided_at: 2026-04-21
decided_by: [simon, mario]
context_used:
  - growth-nexus/analyses/2026-04-15-crm-kpi-analysis.md
  - growth-nexus/meetings/2026-04-12-ops-tooling-review.md
question: "Welches CRM setzen wir ab Q2 ein?"
decision: "HubSpot"
rationale: |
  HubSpot hat bessere Integration zu unserem Marketing-Stack (Klaviyo,
  Meta Ads). Pipedrive ist zwar günstiger, aber die manuelle Daten-Pflege
  würde die Ersparnis auffressen. HubSpot-Testphase im März war
  reibungslos. Entscheidung getragen von Sales-Team.
# Domain-Context
entities: [crm, hubspot, pipedrive]
tags: [crm, tooling, q2-planning]
---

# CRM-Tool-Wahl: HubSpot vs Pipedrive

## Frage
Welches CRM setzen wir ab Q2 ein?

## Entscheidung
HubSpot.

## Begründung
(siehe rationale)

## Was wir berücksichtigt haben
- Sales-KPI-Analyse März: Pipeline-Bearbeitung braucht Tool-Support
- Team-Feedback: 4/5 im Sales-Team präferieren HubSpot-UI

## Was sich ändern müsste, um die Decision zu überdenken
- HubSpot-Preis steigt um >30% (Re-Evaluation triggered)
- Marketing-Stack wechselt weg von Klaviyo
```

→ Landet in: `growth-nexus/decisions/dec-2026-04-21-crm-tool.md`

---

## Change Log

- **v1.1 (2026-04-21):** Sensitivity-Werte `self · team · pii` (statt `public · team · pii`); Routing-Tabelle für individuelle Vaults + `shared/`-Folder; Validation-Felder; Defaults pro Type; aktualisierte Folder-Konvention
- **v0.1 (2026-04-20):** Initiales Schema
