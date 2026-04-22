---
description: "F3 Consistency-Check — beantworte die letzte Frage drei Mal mit unabhängigen Reasoning-Strategien, zeige Konvergenz oder Divergenz als Vertrauens-Signal"
---

Der User hat `/verify` aufgerufen. Arguments: $ARGUMENTS (optional: explizite Frage · default: letzte Antwort re-verifizieren)

Dieser Command ist **Lucas Flagship-Feature** gegen Halluzinationen. Die Idee: ein robuster Fakt sollte aus drei unterschiedlichen Reasoning-Strategien dieselbe Antwort hervorbringen. Divergenz = Warnsignal, keine blinde 3x-Wiederholung mit Prompt-Noise.

## Philosophie: drei Winkel, nicht drei Wiederholungen

Plain "3× das Gleiche fragen" ist wertlos — LLM-Context-Attention nivelliert die Attempts. Stattdessen attackieren wir die Frage aus drei **strukturell unabhängigen** Winkeln:

1. **Attempt A — Direct Reasoning**
   Standard-Antwort aus den verfügbaren Sources. So wie du normalerweise antworten würdest.

2. **Attempt B — First-Principles**
   Baue die Antwort von den Grundprinzipien auf. Welche Daten/Fakten sind gesichert? Was folgt daraus logisch? Ignoriere explizit deine ursprüngliche Antwort.

3. **Attempt C — Contrarian Stress-Test**
   Versuche aktiv, die naheliegende Antwort zu **widerlegen**. Welche Evidenz spricht DAGEGEN? Welche alternativen Erklärungen sind plausibel? Gibt es Sources, die widersprechen?

Wenn A, B, C **konvergieren** → hohe Konfidenz.
Wenn sie **divergieren** → du hast eine Warnung, bevor du dich auf die Antwort verlässt.

## Dein Vorgehen

### 1. Scope bestimmen

- **`/verify`** (kein Argument) → re-verify die Frage, die zu deiner **letzten Antwort** geführt hat. Nenne diese Frage explizit am Anfang.
- **`/verify <frage>`** → explizite neue Frage
- **`/verify last-decision`** → stress-teste die letzte Decision-Log-Entscheidung

Wenn mehrdeutig, frage zurück.

### 2. Kontext fixieren

Bevor die 3 Attempts laufen: **liste explizit** den Kontext auf, mit dem du arbeitest:

```
🎯 Frage: "Welches CRM sollten wir ab Q2 nutzen?"

📚 Kontext, auf den ich zurückgreife:
- dec-2026-04-15-crm-tool.md (authority: approved)
- growth-nexus/analyses/2026-04-15-crm-kpis.md (authority: approved)
- ryzon-context-vault/simon/learnings/2026-04-18-hubspot-test.md (authority: draft)

Alle 3 Attempts nutzen diesen identischen Kontext — nur die Reasoning-Strategie variiert.
```

Das ist wichtig: Luca muss sehen, dass nicht zufällig 3 verschiedene Source-Sets herangezogen werden.

### 3. Drei Attempts generieren

Gib jedes Attempt in einer eigenen klar markierten Sektion aus.

**Format:**

```markdown
## Attempt A — Direct Reasoning

Auf Basis der Sources und ohne Umwege: <Antwort, 2-4 Sätze>

**Kern-Aussage:** <ein Satz>

---

## Attempt B — First-Principles

Lass mich von den gesicherten Fakten aus aufbauen:
- Fakt 1: <aus dec-2026-04-15 ...>
- Fakt 2: <aus analyses/...>
- Fakt 3: <...>

Daraus folgt: <Antwort, logische Kette>

**Kern-Aussage:** <ein Satz>

---

## Attempt C — Contrarian Stress-Test

Was spricht GEGEN die naheliegende Antwort?
- Gegenevidenz 1: <oder: "Keine Gegenevidenz in den Sources gefunden">
- Gegenevidenz 2: <...>

Alternative Erklärungen: <...>

**Kern-Aussage:** <ein Satz — auch wenn sie identisch zu A/B ist>
```

**Wichtig beim Schreiben:**
- **Jedes Attempt ist eigenständig** — nicht "siehe oben". Auch wenn es redundant wirkt.
- **Vermeide Anchoring auf A in B/C** — starte die Gedankenkette jedes Mal von vorne
- **Sei ehrlich bei C**: wenn du wirklich keine Gegenevidenz findest, sag das. Nicht künstlich konstruieren.

### 4. Delta-Analyse

Nach den 3 Attempts: strukturierter Vergleich.

```markdown
## Delta-Analyse

| Aspekt | Attempt A | Attempt B | Attempt C |
|---|---|---|---|
| Kern-Aussage | HubSpot | HubSpot | HubSpot (kein Gegenargument) |
| Zeithorizont | Q2 | Q2 | Q2 |
| Key-Begründung | Klaviyo-Integration | Integration + Sales-UX | — |
| Caveats erwähnt | Preis | Preis, Training | Lock-in-Risiko |

**Konvergenz-Score: 0.85 (hoch)**
- Alle 3 kommen auf identische Kern-Aussage
- B und C ergänzen C mit zusätzlichen Caveats, die A ausgelassen hat
- Kein grundlegender Widerspruch
```

### 5. Konfidenz-Bewertung + Handlungsempfehlung

Basierend auf der Delta-Analyse:

```markdown
## Verdict

🟢 **Hohe Konfidenz (0.85)**

Die Antwort ist robust über drei unabhängige Reasoning-Strategien.
Der Kontext ist konsistent und widerspruchsfrei.

**Was dir die Analyse noch zeigt:**
- Attempt B hat einen Aspekt (Training-Aufwand) hervorgehoben, den Attempt A ausließ
  → falls du die Antwort an Sophie/Luca weitergibst, erwähne das explizit
- Attempt C fand kein substanzielles Gegenargument → die Decision ist solide

**Empfehlung:** Du kannst dich auf die Antwort verlassen. Wenn du sie in
einer Decision dokumentierst (`/decision`), kann sie mit authority=approved gesetzt werden.
```

**Andere Szenarien:**

```markdown
🟡 **Mittlere Konfidenz (0.55)**

Attempts A und B stimmen überein, aber Attempt C findet substanzielle
Gegenevidenz (konkret: "HubSpot-Preis steigt in Q3 lt. Email von Vendor-Kontakt").

**Empfehlung:** Bevor du dich festlegst, prüfe die Quelle der Gegenevidenz
explizit. Soll ich `/find HubSpot Preis` laufen lassen?
```

```markdown
🔴 **Niedrige Konfidenz (0.30)**

Die drei Attempts divergieren signifikant:
- Attempt A: HubSpot
- Attempt B: Pipedrive (basierend auf Kostenanalyse)
- Attempt C: "Noch nicht genug Daten für eine Entscheidung"

**Empfehlung:** Antwort ist nicht belastbar. Bitte verlasse dich NICHT
darauf, ohne weitere Recherche. Mögliche Gründe:
- Sources widersprechen sich
- Sources sind unvollständig
- Frage ist zu breit formuliert

Schlag vor: `/capture note contested-decision` oder weitere Research.
```

### 6. Protokollierung (optional)

Am Ende: frage den User, ob das Verify-Ergebnis gespeichert werden soll.

```
Möchtest du diese Verify-Analyse speichern?
- Als `verify`-Artefakt in `ryzon-context-vault/<author>/verifications/`
- Verlinkbar aus Decision via `verified_by: <artifact-id>`
- Hilft beim Retro-Review der Woche: "wo war Claude unsicher?"
```

Wenn ja: schreibe das komplette verify-Output als `.md` mit Frontmatter:

```yaml
---
type: verification
date: 2026-04-21
author: sophie
maturity: operational
authority: approved     # verifications sind per default approved (ihr Zweck ist Qualitätsprüfung)
sensitivity: team
source: derived
lifespan: durable       # Historie ist wertvoll
question: "Welches CRM sollten wir ab Q2 nutzen?"
verified_target: dec-2026-04-15-crm-tool.md
convergence_score: 0.85
verdict: high_confidence
---
```

## Wichtige Regeln

1. **Niemals die 3 Attempts zu schnell durchrauschen** — jeder muss echte Gedankenarbeit sein, nicht Copy-Paste
2. **Attempt C muss ehrlich sein** — künstlich erfundene Gegenargumente sind schlimmer als "keine gefunden"
3. **Konfidenz-Score ist kein hartes Maß** — gib einen qualitativen Wert (niedrig/mittel/hoch) mit Begründung
4. **Bei niedriger Konfidenz: nicht wischiwaschi** — sag explizit "bitte verlass dich nicht darauf"
5. **Kontext-Liste am Anfang ist Pflicht** — sonst ist verify für Luca wertlos

## Anti-Patterns

- Drei identische Antworten mit nur stilistischen Variationen → das ist Betrug, nicht Verify
- Attempt C "Alles passt" wenn du nicht ernsthaft gesucht hast → nicht akzeptabel
- Bei niedriger Konfidenz trotzdem eine Entscheidung empfehlen
- Kontext der 3 Attempts variieren (verschiedene Sources) → Invalidiert den ganzen Test
- Verify auf Fragen ohne Repo-Context (reine Allgemeinwissen-Fragen) → sagen dass das nichts bringt, stattdessen Sources laden vorschlagen

## Use-Case-Beispiele

**Gut geeignet:**
- Vor einer wichtigen Decision (`/verify "soll ich X machen?"` → dann `/decision`)
- Nach einer überraschenden Antwort ("hmm, das klingt komisch, `/verify`")
- Bei Team-Diskussionen, wo Luca skeptisch ist ("zeig mir die F3-Analyse")

**Nicht sinnvoll:**
- Einfache Fakten-Abfragen ("wer ist Simon's Manager?") → nutz `/pull`
- Kreative Fragen ("schreib mir eine Email") → Verify bringt nichts
- Fragen ohne Repo-Kontext → sag das ehrlich

## Meta

Wenn du feststellst, dass `/verify` oft auf Fragen läuft, wo die Sources widersprüchlich sind: flagge am Ende mit `📝 Meta: Pattern gesehen — domain X hat oft widersprüchliche Sources, ggf. Retro-Thema.`
