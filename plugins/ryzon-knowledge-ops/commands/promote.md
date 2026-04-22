---
description: "Starte den Promotion-Flow für das Friday-Ritual — operative Einträge der Woche in strategisches ai-context überführen"
---

Der User hat `/promote` aufgerufen. Arguments: $ARGUMENTS (optional: zeitraum / scope)

Dieser Command unterstützt das **Friday-Ritual** (Weekly Human Review). Er bereitet eine **Promotion-Kandidaten-Liste** vor, über die Simon mit Sophie und Luca gemeinsam entscheidet.

**Delegiere an den `promotion-reviewer`-Agent.**

## Dein Vorgehen (als promotion-reviewer)

### 1. Parse Arguments

- Kein Argument: default letzte 7 Tage
- `--days N`: letzte N Tage
- `--from YYYY-MM-DD`: seit Datum
- `--domain <X>`: nur in Domain X suchen

### 2. Kandidaten-Sammlung

Scanne via GitHub-Connector folgende Pfade:
- `ryzon-context-vault/shared/**/*.md` (operational + team = höchste Promotion-Wahrscheinlichkeit)
- `ryzon-context-vault/<person>/**/*.md` für alle Personen (operational + self, könnten team-relevant sein)

**Filter:**
- `date` innerhalb Zeitraum
- `maturity: operational` (strategic ist schon promoviert)
- `authority: draft` OR `approved` (official ist schon abgeschlossen)
- **Nicht berücksichtigt:** `sensitivity: pii` (bleibt immer lokal), bereits promovierte Einträge

### 3. Clustering nach Thema

Gruppiere gefundene Files nach:
1. `domain`
2. gemeinsame `entities` (überlappende Arrays)
3. verwandte `tags`

Jeder Cluster bekommt einen sprechenden Namen, z.B.:
- *"Apollo Q2-Campaign (3 Einträge)"*
- *"CRM-Tooling (5 Einträge)"*
- *"Customer-Insights general (2 Einträge)"*

### 4. Pro Cluster: Promotion-Vorschlag formulieren

Für jeden Cluster, schreibe eine strukturierte Empfehlung:

```
🟠 Cluster: "Apollo Q2-Campaign"
   3 operative Einträge, author-overlap: sophie + simon

   Inhalte:
   - sophie/learnings/2026-04-18-apollo-ctr.md (draft)
   - shared/meetings/2026-04-19-apollo-kickoff.md (draft)
   - simon/analyses/2026-04-20-apollo-spend-projection.md (draft)

   🔎 Empfehlung: PROMOTE → ai-context/analyses/2026-04-apollo-q2-summary.md
   Begründung: 3 konvergente Insights derselben Woche, Cross-Author,
   klarer Business-Impact — lohnt sich als strategisches Dokument.

   Alternative: KEEP OPERATIONAL (noch nicht stabil genug für ai-context)
```

### 5. Gesamte Übersicht als Tabelle

Am Ende des Runs:

```
📋 Promotion-Vorschläge für Friday-Ritual (2026-04-21)

| # | Cluster | Files | Empfehlung |
|---|---|---|---|
| 1 | Apollo Q2-Campaign | 3 | 🟢 PROMOTE |
| 2 | CRM-Tooling | 5 | 🟢 PROMOTE |
| 3 | Customer-Calls (Random) | 2 | 🟡 KEEP |
| 4 | Draft-Scratches Simon | 4 | 🔴 DELETE |

Total: 14 operative Einträge der Woche
Vorschlag: 2 Cluster promoten, 1 behalten, 1 löschen

💬 Nächster Schritt: im Friday-Ritual pro Cluster durchgehen,
Entscheidung treffen, dann:
- PROMOTE: File nach ai-context/ schreiben (via meeting-sync-agent-Pattern)
- KEEP: Nichts tun, Cluster bleibt operativ
- DELETE: Files löschen (git rm), Commit "cleanup: delete stale drafts"
```

### 6. Nach der Friday-Ritual-Entscheidung

Wenn User nach der Diskussion sagt *"Cluster 1 promoten"*:
1. Fasse die 3 Files zu einem kuratierten Eintrag in `ai-context/` zusammen (neue `analyses/`-Datei oder mehrere kleinere)
2. Setze `maturity: strategic`, `authority: approved`, `source: derived` (weil aus mehreren Quellen aggregiert)
3. Lege `supersedes`-Referenz zu Source-Files an (damit nachvollziehbar)
4. Commit nach `ai-context/` mit Message: `promote: <cluster-name>`
5. Optional: Source-Files in operational bekommen `superseded_by: <neue-id>` Metadatum (oder werden gelöscht)

## Wichtig

- **Promotion ist NIE automatisch** — immer explicit Human-Review
- **Cluster dürfen klein sein** — auch 1 File kann promoviert werden, wenn es stand-alone strategisch ist
- **Keine PII promoten** — Doppel-Check: wenn ein File `sensitivity: pii` hat, gehört es nie in ai-context
- **Meeting-Sync-Pattern reusen:** existing `meeting-sync-agent.md` im ai-context zeigt, wie operativ → ai-context geschrieben wird (commit + push Flow)
- **Nach Promotion:** Original-Files bleiben operativ (mit `superseded_by`), so bleibt Historie erhalten
