# 2-Wochen-Experiment — Knowledge Setup

*Start: nach Freigabe durch Sophie & Luca · Ende: 2 Wochen später*

> Zweck: minimal-invasiv testen, ob das GitHub-first-Setup für Ops/Commercial-Arbeit funktioniert — bevor wir Mario und den Berater onboarden oder zur Hybrid-Architektur wechseln.

---

## Scope

**In scope**
- Sophie & Luca nutzen aktiv
- 1 gemeinsames GitHub-Repo (`ryzon-knowledge-ops`, privat)
- 1 gemeinsames Claude Project mit GitHub-Connector
- 4 Plugin-Commands: `/capture`, `/decision`, `/pull`, `/sources`
- Frontmatter-Schema festgelegt (siehe Status-Doc §7)

**Out of scope**
- Mario & externer Berater (kommen ab Woche 3)
- Marios-Bierdeckel-Erfassung (eigener Epic)
- Firestore-Anbindung (später in Hybrid-Phase)
- Graph-Retrieval (Q3+)
- Context Packs (ab Woche 5)

---

## Preconditions — bevor Woche 1 startet

| # | Was | Wer | Aufwand |
|---|---|---|---|
| 1 | Repo `ryzon-knowledge-ops` in Ryzon-Org anlegen (privat) | Simon | 5 Min |
| 2 | README mit Frontmatter-Schema + Tag-Taxonomie | Simon | 30 Min |
| 3 | Plugin-Skelett uploaden via Claude App Directory | Simon | 15 Min |
| 4 | Claude Project erstellen, GitHub-Connector aktivieren, Instructions laden | Simon | 20 Min |
| 5 | Sophie & Luca zu Repo + Project einladen | Simon | 5 Min |
| 6 | 15-Min Kick-off: *"so nutzt ihr es"* — live demo `/capture` + `/decision` | alle | 15 Min |

**Total bis Go-live: ~1,5 Stunden für Simon, 15 Min für Sophie/Luca**

---

## Woche 1 — Fundament

### Tägliche Routine (pro Person, ~30 Min/Tag)
- **Morgens:** Claude Project öffnen, `/pull <domain>` für aktuelle Aufgabe → loslegen
- **Während der Arbeit:** bei jedem nicht-trivialen Insight → `/capture learning "..."`
- **Am Ende einer Entscheidung:** → `/decision "..."` mit Begründung
- **Nach jeder Antwort, die relevant ist:** kurz prüfen ob Quellen-Liste (F4) sinnvoll aussieht

### Ziele Woche 1
- [ ] Mindestens **10 Einträge pro Person** im Repo (Notes/Learnings/Decisions)
- [ ] Mindestens **3 Decisions** mit vollständigem Schema
- [ ] Mindestens **1 "Connection across domains"**-Moment (Sophie findet etwas Relevantes aus Lucas Einträgen)
- [ ] Keine offenen Fragen zum Workflow (wenn doch → Slack-Channel `#knowledge-ops-experiment`)

### Mid-week Check-in
**Mittwoch 30 Min** — gemeinsames Screen-sharing:
- Wie viele Einträge?
- Was war reibungslos?
- Was hat genervt?
- 1 Anpassung (Schema, Command, Instructions) ableiten und umsetzen

---

## Woche 2 — Gemeinsames Nutzen

### Erweiterte Routine
- Woche-1-Routine weiter
- Zusätzlich: **täglich einmal Kontext des anderen konsumieren** — z.B. Luca fragt: *"Was hat Sophie diese Woche zu Apollo gecaptured?"*
- **Decision-Log aktiv nutzen** — vor neuen Entscheidungen prüfen: *"Haben wir das schon mal entschieden?"*

### Ziele Woche 2
- [ ] Mindestens **15 Einträge pro Person**
- [ ] Mindestens **5 Fälle**, in denen Claude aus den Einträgen des anderen zitiert
- [ ] Mindestens **1 Decision**, die durch das Decision-Log-Lookup verbessert wurde
- [ ] Erste Retrieval-Probleme identifiziert (*"Claude hat X nicht gefunden, obwohl's da war"*)

### Friday-Retro
**Freitag 45 Min** — strukturiertes Debrief (siehe Evaluation unten)

---

## Messkriterien

### Quantitativ
| Metrik | Ziel Woche 1 | Ziel Woche 2 |
|---|---|---|
| Einträge pro Person | ≥10 | ≥15 kumuliert |
| Decisions mit vollem Schema | ≥3 | ≥5 kumuliert |
| Cross-domain-Zitate (Sophie↔Luca) | — | ≥5 |
| `/sources`-Block als hilfreich empfunden (1-5 Skala, pro Antwort) | ⌀ ≥3 | ⌀ ≥4 |
| Retrieval-Fehler gemeldet | n.a. | <3 blocker |

### Qualitativ — Trust Battery Retrospective

Nicht automatisiert, sondern am Ende jeder Woche gemeinsam beantwortet:

**Woche 1 — wo steht die Battery?**
- 20% (Pair mode): ich reviewe jede Antwort
- 40% (Async + Checkpoints): ich lasse Claude laufen, stoppe an wichtigen Punkten
- 60% (Full delegation + Audit): end-to-end mit Spot-Check
- 80%+ (Autonomous): Claude fragt selbst, wenn unsicher

Sophie-Rating: __ % · Luca-Rating: __ % · Simon-Rating: __ %

**Woche 2 — ist die Battery gestiegen, gefallen oder flach?**
- ⬆ gestiegen → was hat Vertrauen gebaut?
- ⬇ gefallen → was hat es untergraben?
- → gleich → fehlt ein Vertrauens-Hebel?

---

## Friday-Retro Struktur (Woche 2)

**45 Min. Agenda:**

1. **Zahlen ansehen** (5 Min) — Einträge, Decisions, Nutzung
2. **Was hat funktioniert?** (10 Min) — silent writing + Runde
3. **Was hat genervt?** (10 Min) — silent writing + Runde
4. **Trust Battery** (5 Min) — individuelle Einschätzung (siehe oben)
5. **Was hat überrascht?** (5 Min) — offene Runde
6. **Entscheidung** (10 Min) — eine von drei Richtungen:
   - **A — Weitermachen & skalieren:** Mario onboarden, Woche 3 erweitern
   - **B — Iterieren:** Setup anpassen, 1 weitere Woche Test
   - **C — Pivot:** anderes Setup versuchen, GitHub-first war nicht richtig

---

## Abort-Kriterien — wann brechen wir ab

Wir stoppen das Experiment vorzeitig, wenn:
- Nach Woche 1 **weniger als 5 Einträge** pro Person → Friktion zu hoch
- Luca hat das Vertrauen am Ende Woche 1 **signifikant verloren** (battery sinkt auf <20%) → Setup falsch für sein Profil
- **Technische Blocker** blockieren die tägliche Nutzung >2 Tage (GitHub-Sync, Plugin-Bug)

Ehrliches Abbrechen ist besser als "durchhalten".

---

## Verantwortlichkeiten

| Wer | Rolle |
|---|---|
| **Simon** | Setup, Plugin-Pflege, Mid-week Check-in moderieren, Friday-Retro facilitieren, Blockers lösen |
| **Sophie** | aktive Nutzung, Feedback in Retros, ehrliche Battery-Einschätzung |
| **Luca** | aktive Nutzung, Vertrauens-Signale explizit benennen, Schema-Verbesserungen vorschlagen |
| **Mario** | nicht im Experiment — wird gebrieft, falls Sophie/Luca Entscheidungen mit ihm abstimmen müssen |

---

## Parallel-Epics (nicht blockierend)

Während das Experiment läuft, laufen parallel:
- **Marios Bierdeckel-Session** — 1h mit Mario, eigener Ansatz für Tribal Knowledge
- **Hybrid-Architektur prototypen** (low priority) — GitHub-Action-Mirror nach Firestore vorbereiten, damit Woche 3+ sauberer Übergang möglich

---

## Ergebnis des Experiments

Am Ende der 2 Wochen liegt vor:
1. Ein **funktionierendes Repo** mit ~50+ Einträgen, das weiter wächst
2. **Konkrete Zahlen** zur tatsächlichen Nutzung
3. Eine **Trust-Battery-Entwicklung** über 2 Wochen für jede Person
4. Eine **klare Entscheidung** (A/B/C oben) mit Begründung
5. **Lessons für Mario-Onboarding** und Hybrid-Phase

Dieses Dokument wird am Retro-Freitag ergänzt mit den tatsächlichen Zahlen und der getroffenen Entscheidung.
