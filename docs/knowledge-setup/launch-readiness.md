# Launch-Readiness · Knowledge Setup

*Für Meeting mit Sophie & Luca · Stand: 2026-04-21*

> Was muss fertig sein, bevor ihr zwei mit dem Setup arbeiten könnt — und bis wann das realistisch ist.

---

## Offene Items nach Kategorie

### 🟠 Input aus heutigem Meeting (Sophie + Luca)

Wir brauchen eure Entscheidung zu 5 Punkten (Details im Diagramm-Doc):

1. **Decision-Log-Schema** — welche Felder final
2. **Transparenz-Block** — default sichtbar oder nur auf `/sources`
3. **Promotion-Rechte** — wer darf strategisch machen
4. **Tag-Taxonomie** — frei vs kontrolliert
5. **Mario-Visibility** — was ab Woche 3 sichtbar

**→ Ergebnis heute:** 5 Entscheidungen fließen in Plugin + Project Instructions

---

### 🔴 Pre-Rollout (Simon solo, kritisch)

| Item | Aufwand |
|---|---|
| Bug-Fix: doppelte `tags`-Keys in ~30 Files | 1 h |
| Curation: private Granola-Notizen trennen | 2–3 h |
| `growth-nexus`-Struktur erweitern (`private/`, `decisions/`, `schema/`) | 30 min |
| Neues Repo `ryzon-context-vault` + Obsidian-Config | 1 h |
| Schema mit 5 MVP-Dimensionen finalisieren | 1 h |
| Plugin-Commands auf 5-Felder-Schema updaten | 1–2 h |
| Agent `dimension-enricher` (Default-Setter) | 2 h |
| Agent `decision-facilitator` (Schema-Interview) | 2 h |
| Install-Script + README | 3 h |
| Claude Project Instructions finalisieren | 1 h |
| Team-README für euch beide | 1 h |
| **Summe** | **~15–18 h · 2–3 Fokus-Tage** |

---

### 🟡 Kann nach Launch kommen

- `entity-linker`-Agent (Auto-Wiki-Links) — Woche 2
- `promotion-reviewer`-Agent — **vor 1. Freitag-Ritual**
- `/promote`-Command — **vor 1. Freitag-Ritual**
- Obsidian-CLI-Integration — Woche 2

---

## Timeline-Szenarien

Heute = **Dienstag 21.04.2026**

| Szenario | Pre-Rollout | Install-Session | Start Woche 1 | 1. Friday-Retro |
|---|---|---|---|---|
| **⚡ Aggressiv** | Di abend + Mi + Do | Fr 24.04 | Mo 27.04 | Fr 01.05 (Feiertag!) → Do 30.04 vorziehen |
| **✅ Realistisch** | Mi + Do | Mo 27.04 | Di 28.04 | Fr 08.05 |
| **🧘 Komfortabel** | Mi–Mo | Di 05.05 | Mi 06.05 | Fr 15.05 |

---

## Empfehlung: **Szenario ✅ Realistisch · Launch Di 28.04**

**Warum:**
- Mi + Do = 2 Fokus-Tage für Simon, genug Puffer für Bug-Fixes
- Fr = Buffer für Edge Cases, Wochenende als Safety-Net
- Install-Session Mo 27.04 Vormittag (ruhig), echter Start Di 28.04
- 1. Friday-Retro am **Fr 08.05** (nicht 01.05 wegen Feiertag)
- `promotion-reviewer` + `/promote` werden in Woche 1 parallel fertig — sind da zum 1. Retro

**Was das voraussetzt:**

| Wer | Commitment |
|---|---|
| **Sophie & Luca** | Heute Entscheidung zu den 5 offenen Punkten · Mo 27.04 je 30 Min für Install verfügbar |
| **Simon** | Mi + Do ~7 h Fokus-Arbeit · Fr als Puffer blockhalten |
| **Alle** | Freitag 08.05 14:00–14:45 als 1. Friday-Retro im Kalender |

---

## Alternativ-Vorschlag: Aggressiv Mo 27.04

Wenn ihr alle früher Gas geben wollt und Simon heute Abend schon loslegt:
- Pre-Rollout Di/Mi/Do komprimiert
- Install Fr 24.04
- Start Mo 27.04
- 1. Retro Do 30.04 (wegen Feiertag am 01.05)

**Risiko:** weniger Puffer bei unerwarteten Problemen · Qualität der Agents evtl. unterhalb Standard

---

## Frage an euch

1. Passt Szenario **Realistisch** mit Start Di 28.04?
2. Habt ihr Kalender-Konflikte mit Mo 27.04 für die Install-Session?
3. Fr 08.05 14:00–14:45 als wiederkehrender Slot für Friday-Retro → einverstanden?
