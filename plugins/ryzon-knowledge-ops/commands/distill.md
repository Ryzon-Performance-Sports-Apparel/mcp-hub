---
description: "Destilliere die aktuelle Chat-Session — extrahiere Key-Insights, Decisions, Open Questions und biete Speichern an"
---

Der User hat `/distill` aufgerufen. Arguments: $ARGUMENTS (optional: scope-hint, z.B. "nur das letzte Thema")

Dieser Command addressiert den Schmerz *"ich hatte 2 Stunden Chat und die Insights sind begraben"*. Du machst einen **strukturierten Digest** der Session, bereit zum Speichern.

## Dein Vorgehen

### 1. Scope bestimmen

- Kein Argument: analysiere die **gesamte laufende Session** (alle Nachrichten seit Session-Start)
- Mit Argument wie `"nur Apollo"`: fokussiere auf Teile der Session, die zum Thema passen
- Mit Argument `"last N"`: letzte N Nachrichten

### 2. Strukturierten Digest generieren

Extrahiere und formatiere in diese Abschnitte:

```markdown
# Session-Digest · <YYYY-MM-DD HH:MM>

## Kontext
<1–2 Sätze: worum ging es in dieser Session>

## Key Insights
- [Insight 1, 1 Satz]
- [Insight 2]
- [Insight 3]
(max 5, die wichtigsten)

## Entscheidungen (falls getroffen)
- [Entscheidung 1] — Begründung
- [Entscheidung 2]
(falls keine: weglassen)

## Action Items
- [ ] [Aktion 1] — Owner: <person>
- [ ] [Aktion 2]

## Offene Fragen
- [Frage 1]
- [Frage 2]

## Referenzen
- Quelle X (file: …)
- Externe Links falls erwähnt

## Session-Metadaten
- Dauer: ~<X> Minuten / <Y> Nachrichten
- Hauptdomains: [sales, crm, ...]
- Erwähnte Entities: [apollo, hubspot, ...]
```

### 3. Qualität-Kriterien für den Digest

- **Knapp, nicht detailliert** — der Digest ist eine Zusammenfassung, keine Transkription
- **Insights > Chronologie** — nicht "dann hast du X gefragt, dann habe ich Y geantwortet"; sondern *was ist das Wertvolle*
- **Entscheidungen prominent** — falls welche in der Session entstanden sind
- **Unsicherheit markieren** — Wenn Claude sich unsicher war, im Insight anmerken

### 4. Bestätigung + Speicher-Angebot

Nach dem Digest:

```
📝 Digest generiert. Was möchtest du damit tun?

Optionen:
1. `/capture learning <digest>` — als persönliches Learning speichern (→ dein Vault)
2. `/capture meeting <digest>` — als Meeting-Protokoll speichern (→ shared/)
3. `/decision <...>` — falls eine Entscheidung drin ist, strukturiert als Decision
4. Nur anzeigen, nicht speichern
5. Neu generieren mit anderem Scope

Empfehlung: [Option X, basierend auf Inhalt]
Begründung: [warum]
```

### 5. Wenn User sich für Speichern entscheidet

- Delegiere an `/capture` oder `/decision` mit dem Digest als Content
- **`/distill` setzt KEINE eigenen 5-Dimensionen** — das macht `dimension-enricher` via `/capture`

## Spezialfall: Multi-Topic-Sessions

Wenn die Session mehrere klar getrennte Themen hatte:
- Biete an: *"Die Session deckt 3 Themen ab (Apollo, CRM, Q2-Planning). Soll ich pro Thema einen separaten Digest machen?"*
- Jeden als eigenen potentiellen `/capture` behandeln

## Wichtig

- **Halluziniere nicht** — was nicht in der Session stand, kommt nicht in den Digest
- **Bei sehr langen Sessions** (>100 Nachrichten): warn, dass du nicht alles im Detail abgedeckt haben könntest
- **PII-Aware** — wenn die Session private 1on1-Inhalte hatte (Gesundheit, HR), schlage vor: *"Dieser Digest enthält sensibles. Empfehlung: /capture mit sensitivity: pii → landet in private/"*
- **Source-Block erwähnen** — der Digest sollte selbst kein `/sources`-Block haben, aber Claude soll die Files erwähnen, die in der Session herangezogen wurden
