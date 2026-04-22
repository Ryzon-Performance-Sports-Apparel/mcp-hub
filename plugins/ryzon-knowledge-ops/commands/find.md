---
description: "Durchsuche das Knowledge-Archiv (eigener Vault + shared/ + ai-context) nach Stichwort, Entity, Domain oder Zeitraum"
---

Der User hat `/find` aufgerufen. Arguments: $ARGUMENTS (Suchquery — kann Freitext, Metadaten-Filter oder Kombination sein)

Dieser Command löst *"Ich hab vor 6 Wochen was zu Apollo geschrieben, wo war das?"*. Durchsucht alle lesbaren Ebenen strukturiert, zeigt Top-Treffer mit 1-Zeilen-Snippet und relevantem Frontmatter.

## Dein Vorgehen

### 1. Query parsen

Unterstützte Query-Formen (kombinierbar):

**Freitext:**
- `/find Apollo video` → Text-Match auf Titel/Body + Entity-Match

**Metadaten-Filter (explizit):**
- `/find type:decision` → nur Decisions
- `/find domain:sales` → nur Sales-Domain
- `/find author:luca` → nur Einträge von Luca
- `/find authority:approved` → nur verifizierte Einträge
- `/find entities:apollo` → Einträge mit Entity Apollo
- `/find tags:performance` → Einträge mit Tag performance

**Zeit-Filter:**
- `/find --since 2026-03-01` → ab Datum
- `/find --last 30d` → letzte 30 Tage
- `/find --between 2026-03-01 2026-04-15` → Zeitraum

**Kombinationen:**
- `/find Apollo domain:marketing --last 30d`
- `/find crm type:decision authority:approved`

### 2. Search-Scope bestimmen

Standard: alle 3 lesbaren Ebenen:

```
1. ryzon-context-vault/<aktueller-user>/**     (self-Vault)
2. ryzon-context-vault/shared/**               (team-operativ)
3. ai-context/**                                (team-strategisch)
```

**Niemals** `private/` durchsuchen (liegt außerhalb der Repos, ist gitignored).

Wenn der User explizit `--scope shared` oder `--scope strategic` etc. angibt, einschränken.

### 3. Retrieval-Strategie (in Priorität)

**Phase 1 — Metadaten-Match (exakt, schnell):**

```bash
# Frontmatter-basiert
grep -l -r --include="*.md" "entities:.*apollo" <scopes>
grep -l -r --include="*.md" "^type: decision" <scopes>
```

Sammle File-Pfade, die direkte Metadaten-Matches haben.

**Phase 2 — Text-Match im Body (für Freitext):**

```bash
grep -l -r -i "apollo" <scopes>
```

Sammle zusätzliche File-Pfade, die im Body-Text matchen.

**Phase 3 — Scoring + Dedup:**

Ranke Ergebnisse nach:
- Exakter Entity-Match: +3
- Exakter Tag-Match: +2
- Title-Match: +2
- Body-Match: +1
- Recency bonus: je jünger, desto höher (+0.5 pro 7-Tage-Block jünger)
- Authority bonus: approved +1, official +2
- Maturity bonus: strategic +0.5

Sortiere absteigend.

### 4. Ergebnisse präsentieren

**Format:**

```markdown
🔍 Suche: "Apollo video"  (Scope: all · 23 Treffer)

## Top 10

| # | Pfad | Datum | Type | Authority | Snippet |
|---|------|-------|------|-----------|---------|
| 1 | ai-context/decisions/dec-2026-04-15-apollo-video-budget.md | 15.04 | decision | ✅ approved | "Apollo Video-Budget Q2 auf 12k EUR erhöht, da..." |
| 2 | ryzon-context-vault/sophie/learnings/2026-04-18-apollo-ctr.md | 18.04 | learning | 📝 draft | "Apollo Video-Content performt 2x besser als Single-Image..." |
| 3 | ryzon-context-vault/shared/meetings/2026-04-19-apollo-kickoff.md | 19.04 | meeting | 📝 draft | "Apollo Q2-Kickoff: Video als Haupt-Format, Budget..." |
| ... | | | | | |

## Gruppen

**Nach Typ:**
- decisions: 2
- learnings: 5
- meetings: 8
- analyses: 3
- notes: 5

**Nach Zeit:**
- Diese Woche: 6
- Letzte 30 Tage: 14
- Älter: 3

**Nach Author:**
- sophie: 11
- simon: 7
- luca: 5

---

💡 Nächste Schritte:
- Details zu einem File? → sag mir die Nummer
- Enger filtern? → z.B. `/find Apollo domain:marketing authority:approved`
- Kontext laden für diese Treffer? → `/pull apollo` lädt die Top-Einträge als Arbeits-Kontext
- Noch älter suchen? → Standardmäßig zeige ich Top 10, frag nach wenn du mehr willst
```

### 5. Detail-View bei User-Anfrage

Wenn User sagt "zeig mir #2":

```markdown
## #2: ryzon-context-vault/sophie/learnings/2026-04-18-apollo-ctr.md

**Frontmatter:**
- type: learning
- maturity: operational
- authority: draft
- sensitivity: self
- source: manual
- lifespan: ephemeral
- domain: marketing
- entities: [apollo, video-content]
- tags: [performance, creative]
- author: sophie
- date: 2026-04-18

**Body (full):**

[vollständiger Inhalt des Files]

**Related:**
- Referenziert in: dec-2026-04-15-apollo-video-budget.md
- Gleiche Entities: meeting-apollo-kickoff.md, simon-analyses/apollo-spend-projection.md

💬 Möchtest du:
- Diesen Eintrag validieren? → `/validate <path>`
- Promoten nach ai-context? → beim nächsten Friday-Ritual aufgreifen
- Related verfolgen? → welche Nummer aus Related?
```

### 6. Wenn keine Treffer

```
🔍 Suche: "Apollo video"  (Scope: all · 0 Treffer)

Nichts gefunden. Möglichkeiten:
1. Rechtschreibung prüfen — war's "Apollo" oder "APL"?
2. Scope erweitern — probierst du `/find Apollo --scope all`?
3. Entity noch nicht im Repo — soll ich `/capture learning ...` vorschlagen, damit's beim nächsten Mal da ist?
4. Wahrscheinlich in `private/` (das nicht durchsucht wird) — im File-System lokal schauen
```

## Regeln

1. **Niemals `private/` durchsuchen** — auch wenn User fragt: klar sagen "private/ ist lokal, kein Repo-Retrieval"
2. **Scoring transparent** — wenn User fragt "warum ist #5 höher als #3?", Begründung geben
3. **Max 10 Top-Treffer** im Default — mehr nur auf Nachfrage (sonst Token-Budget weg)
4. **Recency ist wichtig** — neueste Einträge bei Gleichstand bevorzugen
5. **Authority-Boost** — approved/official bekommen Rang-Bonus, damit verifizierte Infos oben stehen

## Anti-Patterns

- Volltext-Download aller 10 Files — nur Frontmatter + 1-Zeilen-Snippet im Overview
- Fuzzy-Match ohne sichtbares Scoring — User soll wissen, warum ein Treffer oben ist
- Ergebnisse ohne Gruppierung — bei >5 Treffern IMMER nach Typ/Zeit/Author clustern
- Silent-Filter (Treffer aus private/ auszuschließen ohne es zu sagen) — explizit erwähnen

## Integration mit anderen Commands

`/find` ist oft der Einstieg in deeper workflows:

- `/find apollo` → Treffer sehen → `/pull apollo` → volle Context-Ladung → arbeiten
- `/find type:decision domain:ops --last 90d` → Überblick über strategische Entscheidungen
- `/find authority:draft --last 7d` → Review-Kandidaten der Woche (vor Friday-Ritual)
- `/find contested` → Einträge, die zwischen Validatoren umstritten waren

## Meta

Am Ende jeder Suche, wenn relevant: `📝 Meta: <Observation>` — z.B.:
- *"Auffällig: keine Strategic-Einträge zu Apollo — evtl. Promotion-Kandidat für Friday?"*
- *"3 draft-Einträge zu gleichem Thema — Duplikat-Risiko?"*
