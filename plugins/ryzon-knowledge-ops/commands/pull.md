---
description: "Lade relevanten Kontext für eine Domain, Entity oder Scope als Start-Kontext für den Chat"
---

Der User hat `/pull` aufgerufen. Arguments: $ARGUMENTS

Dieser Command lädt gezielt Kontext aus allen lesbaren Ebenen — damit der User mit vollem Kontext in eine Aufgabe startet.

## Dein Vorgehen

### 1. Parse Arguments

Format: `/pull <scope>` wobei `<scope>` sein kann:
- Eine **domain**: `sales`, `marketing`, `product`, `ops`, `customer`, `engineering`, `finance`
- Eine **entity**: `apollo`, `q2-campaign`, `hubspot`
- Ein **type-Filter**: `decisions`, `recent-learnings`
- Ein **Author-Filter**: `from:sophie`, `from:luca`
- Eine **Kombination**: `sales apollo decisions`

Beispiel: `/pull sales apollo`
→ lade alle Einträge wo domain=sales UND entities enthält "apollo"

### 2. Retrieval-Scope: Welche Ebenen durchsuchen

Claude hat Zugriff auf:
1. **User-eigener Vault**: `ryzon-context-vault/<author>/…` — `self` + `team` sichtbar
2. **Team-operativ**: `ryzon-context-vault/shared/…` — `team` sichtbar
3. **Strategisch**: `growth-nexus/…` — `team` sichtbar (Standards, Decisions, validierte Analysen)

**Nicht durchsuchen:** `private/` (liegt außerhalb der Repos).

### 3. Filter-Strategie

Priorität beim Laden:
1. Alle **Decisions** mit `authority: approved` oder `official` zum Scope → immer dabei (Referenz-Punkte)
2. Einträge mit `authority: approved` zuerst
3. Neueste 10 `authority: draft` Einträge zum Scope
4. Bei expliziter Anfrage: `authority: official` only (höchste Verbindlichkeit)

**Maturity-Gewichtung:**
- Strategic-Einträge haben Vorrang bei Team-Standard-Fragen
- Operational-Einträge ergänzen mit aktuellem Stand

### 4. Via Connectors holen

Nutze den GitHub-Connector:
1. Liste Files unter `ryzon-context-vault/<author>/`, `ryzon-context-vault/shared/`, `growth-nexus/`
2. Lies Frontmatter jedes Files
3. Filtere nach Scope (domain, entities, type, author)
4. Lade die vollen Files der Top-Matches (max 20, damit Context-Window nicht überlastet wird)

### 5. Overview strukturiert zurückgeben

Antworte mit:

```
📥 Kontext geladen für: <scope>

**🟢 Strategisch / Decisions (authority: approved):** 3
- dec-2026-04-15-crm-tool — "HubSpot ab Q2"
- dec-2026-03-22-sales-process — "2-stufiger Discovery-Call"
- ...

**🟢 Strategisch / Analysen:** 5
- growth-nexus/analyses/... (verified)
- ...

**🟡 Operativ / Team (shared/):** 4
- shared/meetings/2026-04-20-q2-planning.md — draft
- ...

**🟡 Operativ / <author>:** 6
- <author>/learnings/2026-04-18-... — draft
- ...

Total: 18 Files, ~12k Tokens.

Ich habe jetzt den Kontext im Arbeitsspeicher. Womit willst du starten?

Typische nächste Schritte:
- "Fass die wichtigsten Learnings zusammen"
- "Welche offenen Fragen / Widersprüche siehst du?"
- "Bereite mich auf das nächste Apollo-Meeting vor"
```

### 6. Trust-Level sichtbar machen

Bei jedem aufgelisteten File, zeige:
- 🟢 `maturity: strategic` (Team-Standard)
- 🟡 `maturity: operational`
- ✅ `authority: approved`
- 📝 `authority: draft`
- 🔒 `authority: official`

## Wichtig

- **Nicht mehr als 20 Files auf einmal laden** — sonst Token-Budget weg
- **Bei zu wenig Matches** (<3): sage es ehrlich, schlage vor, den Scope zu erweitern
- **Bei zu vielen Matches** (>30): lade Top-20, sage: *"Es gibt 47 Treffer. Ich habe die Top-20 geladen. Willst du enger filtern?"*
- **Decisions mit `authority: approved`** immer dabei, auch wenn sie strenggenommen nicht zum Scope passen — sie sind Referenz-Punkte
- **Niemals `private/` durchsuchen** — selbst wenn User danach fragt: "Private-Content ist lokal, kein Retrieval via Repos"
