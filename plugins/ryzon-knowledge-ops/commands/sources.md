---
description: "Zeige die Quellen der letzten Antwort — detailliert mit Trust-Level und Einfluss-Bewertung"
---

Der User hat `/sources` aufgerufen.

Project Instructions sollten bei jeder Antwort bereits einen **Quellen-Block** liefern (F4 — Context Audit). Dieser Command ist ein **Fallback**, eine **Detail-Ansicht** und eine **Validierungs-Hilfe**.

## Dein Vorgehen

### 1. Schaue zurück auf deine letzte Antwort

Welche Repo-Files hast du genutzt? Wie hast du sie gewichtet?

### 2. Liefere eine detaillierte Quellen-Tabelle

```
Quellen der letzten Antwort:

| File | maturity | authority | sensitivity | Einfluss | Warum relevant |
|---|---|---|---|---|---|
| dec-2026-04-15-crm-tool.md | 🟢 strategic | ✅ approved | 👥 team | ▶ maßgeblich | Beantwortete die Kern-Frage direkt |
| learning-apollo-ctr.md | 🟡 operational | 📝 draft | 🙂 self | mittel | Kontext zur Apollo-Situation |
| meeting-q2-planning.md | 🟢 strategic | ✅ approved | 👥 team | niedrig | Timeline-Referenz |

**Zusammenfassung:**
- 2 approved, 1 draft
- 1 strategic, 2 operational
- 1 mit entscheidendem Einfluss

**Hinweis:** 1 File war `draft` — die Information ist noch nicht verified. Willst du die Antwort mit `only-approved` neu generieren?
```

### 3. Falls keine Repo-Quellen genutzt

Wenn die letzte Antwort rein auf Allgemeinwissen basierte:

```
Quellen: keine Repo-Inhalte.

Die letzte Antwort basierte auf Allgemeinwissen (nicht Ryzon-spezifisch).
Wenn es einen Repo-Eintrag dazu gibt, hätte ich ihn nutzen sollen.
Soll ich noch einmal prüfen, ob es relevante Einträge gibt?

Tipp: Starte mit `/pull <domain>` um Kontext zu laden.
```

### 4. Falls die letzte Antwort unsicher war

Wenn du in der letzten Antwort markiert hattest *"ich bin mir bei X nicht sicher"* oder eine Decision gesucht hast die nicht da war:

```
⚠️ Unsicherheit in der letzten Antwort:
- X war nicht in den Quellen — ich habe es basierend auf allgemeinem
  Wissen abgeleitet
- Y gab es in zwei widersprüchlichen Versionen (learning-A.md vs
  decision-B.md) — ich habe die approved Decision bevorzugt

Möchtest du dazu eine `/decision` anlegen, um die offene Frage
festzuhalten?
```

### 5. Empfehlungen, falls Qualität niedrig war

- Wenn alle Quellen `draft` waren → schlage vor: *"Diese Antwort basiert auf ungevalidierten Quellen. Möchtest du via `/validate` ein Rating abgeben, bevor wir darauf weiter aufbauen?"*
- Wenn Quellen `pii` wären (aus Versehen zugegriffen) → **DARF NICHT PASSIEREN** → falls doch: Fehler melden, Antwort zurückziehen
- Wenn alle Quellen sehr alt (>90 Tage und `lifespan: ephemeral`) → warnen: *"Quellen sind möglicherweise veraltet — neueste Erkenntnisse fehlen?"*

## Wichtig

- **Lüge nicht über Quellen** — wenn du aus Versehen einen Eintrag falsch zugeordnet hast in der vorherigen Antwort, korrigiere es jetzt ehrlich
- **Wenn unklar, welche Files genutzt wurden:** sag es: *"Ich bin mir nicht sicher, welche Files die Antwort im Detail geprägt haben. Lass mich die Antwort noch einmal mit expliziter Retrieval-Spur generieren — willst du das?"*
- **Authority + Maturity zusammen zeigen** — das gibt ein vollständiges Bild (neue Info vs. Team-Standard)
- **Empfehlung `/validate` erwähnen** wenn viele drafts im Spiel sind
