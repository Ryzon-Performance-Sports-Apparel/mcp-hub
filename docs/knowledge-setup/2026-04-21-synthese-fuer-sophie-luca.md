# Knowledge Setup — Synthese & Vorschlag

*Für Sophie & Luca · 21.04.2026, 11:30*

---

## Was wir gestern gehört haben

**Vier Beobachtungen aus der 30-Min-Session:**

1. Euer Fokus liegt auf **Ops & Commercial** — CRM, Sales-KPIs, Kunden-Verständnis, historische Entscheidungen. Brand/Creative-Kontext wurde bewusst abgelehnt.
2. **"Marios Bierdeckel"** ist ein eigenes Thema — Wissen aus informellen Gesprächen geht verloren.
3. Lucas Kern-Schmerz ist **Vertrauen, nicht Speicherung** — Halluzination, Determinismus, Reproduzierbarkeit, Gewichtung.
4. **Historische Entscheidungen & deren Begründung** war das am höchsten bewertete Kontext-Item — das strukturieren wir als eigenen Typ.

---

## Die Weiche: wo lebt das Wissen?

Drei Architektur-Optionen — alle mit demselben Frontend (Claude Plugin + Claude Project als Interface), nur das Backend unterscheidet sich.

| | **A — Firestore** | **B — GitHub** | **C — Hybrid** |
|---|---|---|---|
| Transparenz | opak 🔴 | voll 🟢 | voll 🟢 |
| Query-Power | stark 🟢 | schwach 🟡 | stark 🟢 |
| Adoption Mario | unsichtbar 🔴 | Files sichtbar 🟢 | Files sichtbar 🟢 |
| Versionierung | — | Git-nativ 🟢 | Git-nativ 🟢 |
| Build-Aufwand MVP | niedrig | niedrig | mittel |
| Skalierung >500 Einträge | 🟢 | 🟡 | 🟢 |

### Empfehlung

> **Start mit Option B (GitHub).** Evolution zu Option C (Hybrid), sobald Volumen oder Query-Bedarf es rechtfertigt.

**Warum:** Lucas Kern-Schmerz ist Transparenz. GitHub liefert das out-of-box — jeder Eintrag ist sichtbar, jede Änderung versioniert, jede Mitwirkung nachvollziehbar. Mario adoptiert leichter, wenn er seine Einträge wiederfindet.

---

## Wie es konkret aussieht (Woche 1)

```
   /capture <type>            Claude Project               Claude nutzt
   /decision <frage>            mit GitHub-                 Context mit
   /pull <domain>               Connector                 Source-Audit
         │                         │                          │
         ▼                         ▼                          ▼
   Plugin schreibt     →   .md Files im          →    Antwort + Quellen-
   strukturierte .md       Repo sichtbar &                Liste am Ende
   mit Frontmatter          diff-bar
```

**Vertrauen-Features ab Tag 1:**
- **Quellen-Transparenz:** Jede Antwort listet die genutzten Files + warum sie relevant waren
- **Trust-Level:** Einträge sind verified · draft · raw markiert — Claude kann auf "nur verified" eingeschränkt werden
- **Decision Log:** Business-Entscheidungen als eigener Typ, hoch gewichtet, werden bei wiederkehrenden Fragen automatisch herangezogen

---

## Das 2-Wochen-Experiment

**Scope:** nur Sophie & Luca. Mario & Berater in Woche 3.

**Woche 1** — Fundament
- GitHub-Repo aufgesetzt, Frontmatter-Schema definiert
- Claude Plugin mit 4 Commands (`/capture`, `/decision`, `/pull`, `/sources`)
- Je 10–15 eigene Einträge aus laufender Arbeit

**Woche 2** — Gemeinsames Nutzen
- Gegenseitig auf Einträge des/der anderen zugreifen
- Decision Log als gemeinsamer Raum
- Friday-Retro: *"Was hat funktioniert, wo ist Reibung?"*

**Was wir messen:**
- Wie oft wird gecapturter Kontext in späteren Chats wieder gezogen?
- Wie oft passiert "Connection across domains" (Sophie findet Relevantes aus Lucas Einträgen)?
- **Trust-Battery-Check:** Hat euer Vertrauen in die Antworten über die 2 Wochen zu- oder abgenommen?

---

## Was wir *nicht* heute lösen

- **"Marios Bierdeckel"** — eigener Epic, dedizierte Session mit Mario
- **Semantic Search** — sauber weggelassen, um Determinismus nicht zu opfern
- **Graph-Retrieval** — Vision für Q3+ (Entitäten, Relationen, komplexe Queries). Das Frontmatter-Schema, das wir jetzt definieren, ist schon graph-kompatibel — kein Rebuild später
- **Ryzon Cockpit** als Ziel-Interface — mittelfristig, nicht jetzt

---

## Was wir von euch brauchen

1. **Bestätigung Option B** als Startpunkt
2. **Decision-Log-Schema** gemeinsam schärfen — welche Felder wirklich Pflicht?
3. **Access Control** für Mario / Berater — was sehen sie, was nicht?
4. **Commit** zum 2-Wochen-Experiment — je 30 Min/Tag Nutzung, Friday-Retros

## Und dann?

Wenn Woche 2 zeigt, dass das Setup trägt → Option C (Hybrid) als Evolution, weitere Commands, Mario onboarden.
Wenn nicht → transparent neu bewerten, parken oder pivotieren.

**Kein großer Bau, bevor der kleine Bau funktioniert.**
