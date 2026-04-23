# Friday-Retro Template

*Wöchentlich · Freitag · async · ~20 Min pro Person*

> Strukturierter Retro + Promotion-Review für das Ryzon Knowledge Ops Experiment.
>
> **Kein Meeting, kein Moderator.** Jede:r füllt die eigene Spalte / den eigenen Block im Laufe des Freitags. Git trackt, wer wann was beigetragen hat. Die Person, die am Freitag zuletzt reinschaut, macht die Konsolidierung (siehe Abschnitt "Nach-Retro-Status").
>
> Erste Person des Freitags: dieses Template nach `growth-nexus/meta/friday-retros/YYYY-MM-DD.md` kopieren + committen. Alle weiteren ziehen per `git pull` den aktuellen Stand, tragen ihren Teil ein, committen + pushen.

---

## Meta

- **Datum:** YYYY-MM-DD
- **Anwesend:** Simon, Sophie, Luca (Mario ab Woche 3)
- **Wochennummer:** 1 / 2 / 3 / …
- **Plugin-Version:** z.B. v0.5.0

---

## Zahlen der Woche

| Metrik | Sophie | Luca | Simon | Ziel Woche | ✓ / ✗ |
|---|---|---|---|---|---|
| Einträge gesamt (`/capture`) | | | | ≥10 / ≥15 | |
| Davon Decisions (`/decision`) | | | | ≥3 | |
| Davon Team-Scope (shared/) | | | | ≥2 | |
| Cross-Reads (andere gezogen) | | | | ≥5 in Woche 2 | |
| `/sources` genutzt (# Antworten) | | | | ≥5 | |
| `/distill` genutzt | | | | ≥2 | |

---

## Promotion-Review

Erste Person: `/promote --days 7` aufrufen, Cluster-Tabelle aus dem Output hier einfügen. Alle tragen eigene Votes ein — per `name: PROMOTE / KEEP / DELETE`.

| # | Cluster | Files | Authors | Empfehlung (Agent) | Sophie | Luca | Simon | Konsens |
|---|---------|-------|---------|--------------------|--------|------|-------|---------|
| 1 | Apollo Q2-Campaign | 3 | sophie + simon | 🟢 PROMOTE | | | | _TBD_ |
| 2 | CRM-Tooling | 5 | simon + luca | 🟢 PROMOTE | | | | _TBD_ |
| 3 | ... | | | 🟡 KEEP | | | | _TBD_ |

**Einstimmiger Konsens → direkt umsetzen.** Wer als letzte:r reinschaut, übernimmt die Umsetzung (siehe Nach-Retro-Status).

**Dissens → in den Slack-Channel.** Begründung kurz unter der Tabelle festhalten, dann via Slack einigen oder nächste Woche re-diskutieren.

### Pro PROMOTE-Entscheidung
- Zusammenfassung-File für `growth-nexus/` — Titel + Kernbotschaft
- `supersedes` auf Source-Files setzen
- Commit: `promote: <cluster-name> (retro YYYY-MM-DD)`

### Pro DELETE-Entscheidung
- Paths bestätigen
- `git rm` + Commit `cleanup: delete stale drafts (retro YYYY-MM-DD)`

---

## Was hat funktioniert?

Jede Person trägt stichpunktartig ein. Keine Diskussion nötig — einfach festhalten.

**Sophie:**
- …

**Luca:**
- …

**Simon:**
- …

---

## Was hat genervt?

**Sophie:**
- …

**Luca:**
- …

**Simon:**
- …

---

## Trust-Battery-Check

Jede:r trägt den eigenen Wert ein, plus ein bis zwei Zeilen Kontext (was hat Vertrauen gekostet oder gebaut).

| Person | Diese Woche | Letzte Woche | Trend |
|---|---|---|---|
| Sophie | __% | __% | ⬆ / ⬇ / → |
| Luca | __% | __% | ⬆ / ⬇ / → |
| Simon | __% | __% | ⬆ / ⬇ / → |

**Kontext pro Person (kurz):**

- Sophie: …
- Luca: …
- Simon: …

---

## Was war überraschend?

Async — jede:r trägt ein, was erwähnenswert ist.

- …
- …
- …

---

## Entscheidungen für die Folgewoche

Pro Retro maximal **3 konkrete Anpassungen** aufschreiben:

1. **[Wer] [Was] [Bis wann]**
2. **[Wer] [Was] [Bis wann]**
3. **[Wer] [Was] [Bis wann]**

Parkplatz für größere Themen (nicht diese Woche):

- …

---

## Nach-Retro-Status (Konsolidierung)

Die Person, die am Freitag zuletzt reinschaut, hakt die Liste ab.

- [ ] Alle einstimmigen PROMOTEs gecommited nach `growth-nexus/`
- [ ] Alle einstimmigen DELETEs entfernt (`git rm`)
- [ ] Dissens-Clusters mit kurzer Begründung in `#knowledge-ops-experiment` gepostet
- [ ] 2–3 Anpassungen für Folgewoche (siehe unten) in Slack angepinnt
- [ ] Retro-File committed nach `growth-nexus/meta/friday-retros/<datum>.md`

**Wer hat konsolidiert:** ___

---

## Entscheidungs-Frame für Woche 2

Nur relevant am Ende Woche 2 (Fr 09.05 laut aktueller Planung):

**A — Skalieren** — Setup funktioniert, Mario onboarden ab Woche 3
**B — Iterieren** — noch 1 Woche Test, dann re-evaluate
**C — Pivot** — GitHub-first-Ansatz funktioniert nicht, anderes Setup versuchen

Entscheidung: **___** · Begründung: ___

---

## Changelog für dieses Template

- v2 (2026-04-23) — async self-service statt moderiertes Meeting
- v1 (2026-04-21) — initial
