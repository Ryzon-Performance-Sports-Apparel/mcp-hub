# Ryzon Knowledge Ops — Team README

*Für Sophie, Luca, Simon · Stand v0.5.0 · 2026-04-21*

> Dein Kompass im Knowledge-Setup. Alle Commands, Folder, FAQ in einem Dokument.

---

## Auf einen Blick

**Was?** Zwei GitHub-Repos + individuelle Obsidian-Vaults + Claude App mit Plugin · alles verbunden, damit Claude euer Team-Wissen kennt und neue Insights strukturiert speichern kann.

**Warum?** Chats sind flüchtig, Wissen geht verloren, Decisions werden nicht wiedergefunden. Das Setup fixt das — mit Transparenz-First-Philosophie (Luca's Priorität).

**Wie?** 9 Slash-Commands im Claude Project. Im Alltag nutzt du 3–4 davon.

---

## Deine 9 Commands

### Täglich genutzt (die Core-Vier)

| Command | Wann nutzen | Beispiel |
|---|---|---|
| `/pull` | Morgens · Kontext für eine Aufgabe laden | `/pull sales apollo` |
| `/capture` | Insight oder Note festhalten | `/capture learning Apollo performt 2x besser mit Video` |
| `/decision` | Business-Entscheidung dokumentieren | `/decision CRM-Tool-Wahl ab Q2` |
| `/sources` | Quellen der letzten Antwort prüfen | `/sources` |

### Periodisch genutzt

| Command | Wann nutzen | Beispiel |
|---|---|---|
| `/distill` | Nach langem Chat: Insights destillieren + speichern | `/distill` |
| `/find` | Altes Material wiederfinden | `/find Apollo video --last 60d` |
| `/validate` | Qualität eines Eintrags bewerten (R/A/C-Ratings) | `/validate <path>` |

### Luca's Trust-Flagship

| Command | Wann nutzen | Beispiel |
|---|---|---|
| `/verify` | Kritische Antwort doppelt prüfen: 3 Reasoning-Strategien | `/verify "sollen wir HubSpot nehmen?"` |

### Für Simon (freitags)

| Command | Wann nutzen | Beispiel |
|---|---|---|
| `/promote` | Friday-Ritual vorbereiten | `/promote --days 7` |

**Pro-Tipp:** Starte deinen Tag mit `/pull <dein-bereich>`. Dann hat Claude alles Relevante im Kontext.

---

## Folder-Struktur auf deinem Laptop

```
~/Documents/projects/context/
├── growth-nexus/              🟢 STRATEGISCH · git · Team-Standards, Decisions
├── ryzon-context-vault/     🟡 OPERATIV · git · Obsidian-Vaults + shared/
│   ├── <dein-name>/         ← DEIN Vault (öffne DIESEN in Obsidian)
│   └── shared/              ← Team-Scratchpad
└── private/                 🔒 NICHT git · nur lokal, 1on1s, HR
    └── <dein-name>/
```

### Was landet wo?

| Wenn du captured... | Landet in... |
|---|---|
| Persönliche Note / Learning | `ryzon-context-vault/<dein-name>/` |
| Team-Meeting-Protokoll | `ryzon-context-vault/shared/` |
| Business-Decision | `growth-nexus/decisions/` |
| 1on1-Notiz, HR, Gehalt | `private/<dein-name>/` (lokal) |
| Strategische Analyse | erst `shared/`, dann via `/promote` → `growth-nexus/` |

**Claude macht das Routing automatisch** basierend auf dem `sensitivity`-Feld. Du sagst einfach was's ist, er überlegt wo's hingehört.

---

## Das 5-Felder-Schema (die wichtigste Zutat)

Jeder Eintrag bekommt 5 Dimensionen im Frontmatter. Claude setzt die Defaults, du kannst überschreiben:

| Feld | Werte | Was es bedeutet |
|---|---|---|
| `maturity` | operational · strategic | Reifegrad |
| `authority` | draft · approved · official | Verbindlichkeit |
| `sensitivity` | self · team · pii | Sichtbarkeit |
| `source` | manual · derived · system | Herkunft |
| `lifespan` | ephemeral · durable | Langlebigkeit |

Mehr Details: siehe `plugins/ryzon-knowledge-ops/docs/frontmatter-schema.md` im mcp-Repo.

---

## Dein täglicher Flow

### Morgen
1. Claude Project öffnen
2. `/pull <domain>` — z.B. `/pull sales` oder `/pull customer apollo`
3. Arbeiten mit Kontext

### Während der Arbeit
- Insight? → `/capture learning <was du gelernt hast>`
- Entscheidung getroffen? → `/decision <frage>`
- Lange Session zu Ende? → `/distill` (bietet Summary + Save)

### Am Ende einer Arbeit
- `/sources` um zu prüfen: welche Files haben die Antworten geprägt? Sind das verified-Quellen?

### Freitag
- 14:00 Friday-Retro mit Simon
- Vorher macht Simon `/promote` → Kandidaten-Liste
- Gemeinsam durchgehen, Trust-Battery-Check

---

## FAQ

### Warum zwei Vaults (nicht ein shared)?

Weil Obsidians Wiki-Links nur innerhalb eines Vaults funktionieren. Wenn du deinen eigenen Vault hast, bleibt dein Graph sauber, deine Plugins deine — aber über die git-Repos hat das Team trotzdem Zugriff auf alles (außer `private/`).

### Kann ich shared/ auch in Obsidian öffnen?

Ja, als **zweiten Vault**. Öffne Obsidian → Vault wechseln → `ryzon-context-vault/shared/` wählen. Aber Default-Workflow: dein Vault + CLI/Claude für shared/.

### Was ist, wenn ich aus Versehen etwas Privates in shared/ committe?

1. Sofort Simon pingen
2. Git-Revert machen: `git revert <commit-hash>`
3. File verschieben nach `private/<dein-name>/`
4. Neu commit + push

**Prävention:** immer kurz prüfen, wohin der Commit geht. `/capture` mit `sensitivity: pii` landet automatisch in `private/` — nie im Repo.

### Wie oft sollte ich /capture nutzen?

~5–10 mal pro Tag in aktiven Arbeitstagen. Ziel Woche 1: ≥10 Einträge. Woche 2: ≥15 kumuliert. Weniger = System wird nicht genug gefüttert.

### Was ist der Unterschied zwischen /capture und /distill?

- `/capture`: du weißt, was du speichern willst → direkt rein
- `/distill`: nach langer Session weißt du *nicht* genau was rausfallen soll → Claude destilliert, du wählst

### Wie finde ich alte Einträge wieder?

Drei Wege:
1. In Obsidian: Tag-Search, Graph-View, Backlinks
2. Via Claude: `/pull <scope>` oder einfach natürlich fragen: "Hab ich vor 2 Wochen was zu Apollo geschrieben?"
3. `/find` (kommt Do 30.04 mit v0.5.0)

### Was ist mit Granola-Meetings?

Das Granola-Plugin syncht automatisch in deinen Vault (`<dein-name>/granola/`). Du musst nichts tun. Beim Friday-Retro gehen wir durch, was davon strategisch wird.

### Kann ich Mario etwas zeigen, das er nicht sehen soll?

Falls ein Eintrag `sensitivity: team` hat, sieht er's ab Woche 3. Falls er's NICHT sehen soll, setze `sensitivity: pii` — landet in `private/` → nur lokal bei dir. Wenn unklar, frag Claude: "Sollte das Mario sehen dürfen?"

### Das Plugin aktualisiert sich — woher weiß ich, was neu ist?

Claude App → Customize → Directory → Plugins → Personal → Version sichtbar. Changelog ist im Plugin-README. Simon postet Updates im Slack-Channel `#knowledge-ops-experiment`.

---

## Trust-Battery — was ist das?

Konzept für graduelle Autonomie. Jeder von uns trackt im Kopf: *"wie sehr vertraue ich Claude's Antworten im Ryzon-Kontext?"*

- **20–40%** — ich reviewe jede Antwort (Pair Mode)
- **40–60%** — ich lass laufen, stoppe bei wichtigen Punkten
- **60–80%** — end-to-end, Spot-Check morgens
- **80%+** — Autonomous

Wir checken wöchentlich im Retro: *ist meine Battery gestiegen oder gefallen?* Das zeigt uns, ob das Setup Vertrauen baut oder untergräbt.

---

## Hilfe

**Slack-Channel:** `#knowledge-ops-experiment`
**Direkt:** Simon pingen
**Docs:** `docs/knowledge-setup/` im `mcp-hub`-Repo
- `meeting-agenda-sophie-luca.md` (unsere Diskussion vom 21.04)
- `launch-readiness.md` (Timeline + Commitment)
- `experiment-plan-wochen-1-2.md` (Messkriterien)
- `friday-retro-template.md` (Struktur fürs Friday-Ritual)

**Willkommen im Setup.** 🚀
