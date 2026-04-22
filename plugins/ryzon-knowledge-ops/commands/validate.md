---
description: "Validiere einen Eintrag mit strukturierten Ratings (Relevance · Accuracy · Completeness) und baue so Vertrauen im Wissens-Stack"
---

Der User hat `/validate` aufgerufen. Arguments: $ARGUMENTS (optional: Pfad zum Ziel-File · default: letzter Eintrag)

Dieser Command löst das *"Wie weiß ich, ob eine Info verlässlich ist?"*-Problem. Jeder Eintrag kann von **mehreren Personen** validiert werden. Pro Validation drei 1–5-Ratings + optionaler Kommentar. Validation-History bleibt erhalten (Array).

## Dein Vorgehen

### 1. Ziel bestimmen

- **`/validate`** (kein Argument) → validiere den zuletzt gecaptureten Eintrag dieser Session
- **`/validate <path>`** → validiere explizit diesen Pfad
- **`/validate last <type>`** → validiere das letzte File eines bestimmten Typs (z.B. `/validate last decision`)

Falls unklar welcher Eintrag: frage zurück mit den 3 letzten Kandidaten.

### 2. Ziel-File laden und Metadaten zeigen

Lies das File und zeige eine knappe Zusammenfassung vor dem Rating:

```
Ziel zur Validierung:
📄 `ryzon-context-vault/sophie/learnings/2026-04-21-apollo-video.md`
   type: learning · maturity: operational · authority: draft
   author: sophie · date: 2026-04-21
   
Inhalt (Vorschau):
   "Apollo Video-Content performt 2x besser als Single-Image..."
   
Bestehende Validations: 0
```

Wenn bereits Validations vorhanden sind, liste sie auf (wer, wann, Ratings, ggf. Kommentar) — der User sieht das Gesamtbild.

### 3. Sequentielles Rating (3 Schritte, EINE Frage pro Turn)

**Wichtig:** niemals alle 3 Ratings auf einmal fragen. Sequentielles Interview baut Präzision.

**Schritt 3a — Relevance:**

> Wie **relevant** ist dieser Eintrag für die aktuelle Team-Arbeit?
> 
>   1 = überhaupt nicht relevant
>   2 = schwach relevant
>   3 = neutral / kontextabhängig
>   4 = relevant
>   5 = hoch-relevant, zentral für aktuelle Entscheidungen

Warte auf Antwort (Zahl 1–5).

**Schritt 3b — Accuracy:**

> Wie **akkurat / korrekt** sind die Inhalte?
> 
>   1 = mehrere Fehler / falsche Aussagen
>   2 = einzelne Fehler
>   3 = grob stimmig, aber ungeprüft
>   4 = akkurat, vertrauenswürdig
>   5 = präzise, gut belegt, belastbar

Warte auf Antwort.

**Schritt 3c — Completeness:**

> Wie **vollständig** deckt der Eintrag sein Thema ab?
> 
>   1 = stark lückenhaft
>   2 = wichtige Aspekte fehlen
>   3 = solide, einige offene Punkte
>   4 = weitgehend vollständig
>   5 = umfassend, keine offenen Fragen

Warte auf Antwort.

**Schritt 3d — Optionaler Kommentar:**

> Kommentar? (optional, kurz — was ist dir aufgefallen, was fehlt, was stimmt nicht?)
> (Leere Antwort = kein Kommentar)

### 4. Validation-Block ins Frontmatter schreiben

**Wichtig — MERGE-SAFE:** bestehende Validations nicht überschreiben, sondern als neuen Array-Eintrag hinzufügen.

Schema:

```yaml
validation:
  - validator: <author der gerade validiert>
    validated_at: 2026-04-21
    relevance: 5
    accuracy: 4
    completeness: 4
    comment: "Klar und belastbar, aber Aspekt B2B fehlt"
```

Wenn das File noch keinen `validation:`-Key hat: neuen Array-Key einfügen.
Wenn es bereits welche gibt: Eintrag an das Array anhängen.

### 5. Authority-Auto-Upgrade

**Entscheidungslogik** (NUR für `authority: draft` → `approved`, niemals automatisch `official`):

```
IF current authority == 'draft':
  IF (relevance >= 4) AND (accuracy >= 4) AND (completeness >= 4):
    IF no prior validation in history has any rating < 3:
      → upgrade authority: draft → approved
      → protokolliere im Commit-Message
  ELSE IF any rating <= 2:
    → flag: authority bleibt draft, zusätzlich tag `needs-review` hinzufügen
```

Zeige die Entscheidung transparent:

```
✓ Validation gespeichert.

Deine Ratings: R5 A4 C4
Alle ≥4 → authority upgrade: draft → approved ✅

Dieser Eintrag gilt jetzt als team-verified und kann von Claude mit
höherem Vertrauen in Antworten genutzt werden.
```

Oder, wenn downgrade-Signal:

```
✓ Validation gespeichert.

Deine Ratings: R4 A2 C3
accuracy < 3 → authority bleibt draft, tag `needs-review` hinzugefügt.

Empfehlung: bevor dieser Eintrag in strategische Decisions einfließt,
sollte jemand die akkurat-Lücke prüfen. Möchtest du einen follow-up
`/capture note` anlegen, der das dokumentiert?
```

### 6. Commit

Commit-Message-Template:

```
validate(<domain>): <title> — R<n> A<n> C<n>[, auth→approved]
```

Beispiele:
- `validate(marketing): Apollo Video-Content performt 2x besser — R5 A4 C4, auth→approved`
- `validate(ops): CRM-Tool-Review — R3 A2 C2 (needs-review)`

### 7. Summary-Output

Am Ende:

```
📊 Validation-Zusammenfassung für <filename>:

| Validator | Datum | R | A | C | Avg | Kommentar |
|-----------|-------|---|---|---|-----|-----------|
| sophie    | 21.04 | 5 | 4 | 4 | 4.3 | Klar und belastbar... |
| luca      | 22.04 | 5 | 5 | 5 | 5.0 |  |

Current authority: approved (seit 2. Validation)
```

## Edge Cases

### Mehrfach-Validation durch denselben User

Wenn `sophie` bereits validiert hat und erneut `/validate` auf demselben File aufruft:
- Frage: *"Du hast diesen Eintrag bereits am [Datum] validiert. Replace oder neue Version anhängen?"*
- Replace: ersetze Sophies Eintrag
- New: hänge neuen Array-Eintrag an (Wert: Neuerung über Zeit dokumentiert)

### Validation mit Widerspruch

Wenn frühere Validation R5 A5 C5 war und neue ist R3 A2 C2:
- **automatisch `contested` Tag hinzufügen**
- Prompt: *"Deine Ratings weichen stark von früheren ab. Ist das ein Reviewer-Wechsel, neue Erkenntnisse, oder kontroverses Thema?"*
- Behavior bei `authority: approved` + widersprüchlicher Validation: **kein Downgrade** (User-Intervention via `/capture note contested ...` empfehlen)

### Validate auf Decision-Einträge

Decisions (type=decision) sind schon authority=approved by default. Validation dokumentiert dann:
- *"Decision nach 4 Wochen noch gültig?"* (follow-up Review)
- Bei R/A/C >= 4: keine Auth-Änderung, aber `last_validated_at` im Frontmatter updated

### File existiert nicht

- Exit mit klarer Fehlermeldung
- Schlage vor: *"`/capture learning ...` um erst einen Eintrag zu erstellen"*

## Regeln

1. **Niemals Ratings ohne User-Input** — Claude darf nicht selbst raten
2. **Validation-History preservieren** — niemals bestehende Einträge überschreiben (außer explizit "replace")
3. **Authority-Upgrade ist konservativ** — nur bei **allen** Ratings ≥4 und **keiner** roten Vergangenheits-Flagge
4. **Downgrade ist manuell** — Agent downgraded nicht automatisch (auch bei schlechten Ratings); User wird gewarnt, Entscheidung bleibt bei Mensch
5. **Transparenz** — User sieht Entscheidungslogik explizit, kein Hidden-Magic

## Anti-Patterns

- Batch-Validation ohne Interview (z.B. "bewerte 5 Files auf einmal") → ablehnen
- Validation ohne konkreten Ziel-File → ablehnen
- Auto-Downgrade authority → verboten, User-Intervention nötig
- Stille Überschreibung bestehender Validation → immer nachfragen
