# Dein Companion in Aktion

> Vom Session-Start bis zur handlungsfähigen Antwort — wie der personalisierte SCM-Agent im Alltag funktioniert.

---

## Was passiert, wenn du eine Session startest?

```mermaid
sequenceDiagram
    participant Du as Du
    participant Agent as AI-Agent
    participant Auth as Authentifizierung
    participant Profil as Kontext-Profil
    participant Sektionen as Kontext-Sektionen

    Du->>Agent: Session starten
    Agent->>Auth: Wer bin ich? (Google Login)
    Auth-->>Agent: andi@ryzon.net

    Agent->>Profil: Profil für Andi laden
    Profil-->>Agent: Rolle: SCM Lead<br/>Primär: Pipeline, Lieferanten, Forecast<br/>Unterstützend: Preise, Produktion, Bestände

    Agent->>Sektionen: Primäre Sektionen laden
    Sektionen-->>Agent: PO-Pipeline (12 offene POs)<br/>Lieferanten (Status aller T1/T2)<br/>Forecast (Q3 Projektion)

    Agent->>Sektionen: Unterstützende Sektionen laden
    Sektionen-->>Agent: Preise (aktuelle Konditionen)<br/>Produktion (4 laufende Aufträge)<br/>Bestände (Reichweiten-Alerts)

    Note over Agent: Kontext zusammenbauen:<br/>Primär = "Dein wichtigster Kontext"<br/>Unterstützend = "Zusätzlicher Kontext"<br/>Hintergrund = "Bei Bedarf verfügbar"

    Agent-->>Du: Bereit!<br/>"Ich kenne deine aktuelle PO-Pipeline,<br/>Lieferantenstatus und Forecasts."
```

**Sekunden, automatisch, bei jedem Session-Start.** Kein Sheet öffnen, kein E-Mail durchsuchen.

---

## Szenario 1: PO-Vorbereitung

### Die Aufgabe

> **Du (Andi):** Ich muss die POs für die Q3-Kollektion vorbereiten. Gib mir einen Überblick.

### Was der Agent weiß (nach Profil-Stufe)

```mermaid
graph TB
    subgraph "Primär — denkt der Agent sofort mit"
        P1["PO-Pipeline\n• 12 offene POs, 485k EUR\n• 3 kritisch (hinter Plan)\n• 2 neue POs nötig für Q3"]
        P2["Lieferanten\n• Petratex: 94% Performance, Kapazität frei\n• LTP: aktuell verspätet (Carvico-Stoff)\n• Stamperia: on track, nächste PO in KW 22"]
        P3["Forecast\n• Triathlon +22% vs. Vorjahr\n• Running stabil\n• Cycling -8%"]
    end

    subgraph "Unterstützend — zieht der Agent dazu"
        S1["Preise\n• Petratex FOB: 38,50 EUR/Stk\n• Carvico: +5% Rohstoffkosten"]
        S2["Produktion\n• 4 laufende Aufträge\n• Tri Suit bei Petratex 60% fertig"]
    end

    style P1 fill:#10B981,color:#fff
    style P2 fill:#10B981,color:#fff
    style P3 fill:#10B981,color:#fff
    style S1 fill:#3B82F6,color:#fff
    style S2 fill:#3B82F6,color:#fff
```

### Die Antwort des Agents

> **Agent:** Hier ist der Q3-Überblick für die PO-Planung:
>
> **Neue POs erforderlich (2):**
> 1. **Tri Suit 2026 Restock** — Petratex, ~1.600 Stück (basierend auf +22% Forecast vs. Vorjahr). Petratex hat Kapazität und aktuelle Performance von 94%. FOB-Preis: 38,50 EUR. Bei PO diese Woche: ETA KW 30.
> 2. **Running Tight Replenishment** — Damen M ist kritisch (45 Stück, 4 Tage Reichweite). Empfehle 1.200 Stück bei Stamperia. On track, nächster freier Slot KW 23.
>
> **Achtung:**
> - LTP Cycling Bib (PO-2026-041) liegt 3 Wochen zurück — Carvico-Stoff verspätet. Soll ich Alternativen prüfen?
> - Carvico-Stoffpreise sind +5% — betrifft alle Aufträge mit Jersey 280g
>
> **Nächste Schritte:**
> - [ ] PO-Mengen für Tri Suit Restock bestätigen
> - [ ] LTP-Verzögerung eskalieren oder Alternative evaluieren
> - [ ] Nilorn Packaging Forecast Q3 bestätigen (Joost/Max, Deadline Freitag)
>
> Soll ich die PO für Petratex vorbereiten?

**Ohne ein einziges Sheet zu öffnen.** Der Agent kennt die Pipeline, die Lieferanten, den Forecast und die Preise.

---

## Szenario 2: Bestandsalarm (Max)

> **Max:** Welche SKUs sind kritisch?
>
> **Agent:** Drei SKUs mit Reichweite unter 7 Tagen:
>
> | SKU | Bestand | Reichweite | Status Replenishment |
> |-----|---------|------------|---------------------|
> | Running Tight Damen M (schwarz) | 45 Stk | 4 Tage | Keine offene PO — **Aktion nötig** |
> | Tri Short Herren L (navy) | 120 Stk | 6 Tage | PO-2026-039 unterwegs, ETA KW 22 |
> | Cycling Jersey Herren S (weiß) | 30 Stk | 5 Tage | Produktion bei LTP verspätet |
>
> Für die Running Tight empfehle ich eine Sofort-PO: 1.200 Stück bei Stamperia, basierend auf den letzten 4 Wochen Sell-Through (Ø 11 Stk/Tag für diese Variante). Soll ich das Ordersheet vorbereiten?

---

## Szenario 3: Lieferanten-Risiko (Laura)

> **Laura:** Wie sieht unsere Abhängigkeit von Carvico aus?
>
> **Agent:** Carvico ist euer Hauptlieferant für Performance-Stoffe:
>
> - **Betroffene Produktlinien:** Triathlon (100% Jersey 280g), Cycling Bib (80% Jersey 220g)
> - **Aktive POs mit Carvico-Material:** 4 Stück, Gesamtwert Materialanteil ~62k EUR
> - **Aktuelles Risiko:** 2 Wochen Verzögerung bei Jersey 280g, betrifft LTP-Produktion (PO-2026-041)
> - **Preisdruck:** +5% Rohstoffkosten YoY
>
> **Diversifizierung:** Eurojersey (Italien) bietet vergleichbare Qualität mit 4 Wochen Lead Time. Bisher kein aktives Lieferantenverhältnis. Soll ich eine Vergleichstabelle für die nächste Sourcing-Bewertung vorbereiten?

---

## Was das im Alltag bedeutet

| Heute | Mit Context Companion |
|-------|----------------------|
| "Moment, ich schau im Sheet nach..." | Agent kennt alle offenen POs |
| "Wie war nochmal der Preis bei Petratex?" | Agent kennt aktuelle Konditionen |
| "Welche SKUs müssen wir nachbestellen?" | Agent hat Bestandsreichweiten parat |
| "Wer ist für den Fabric Order zuständig?" | Agent kennt die Rollenmatrix |
| "Wie ist der Stand bei LTP?" | Agent kennt den Produktionsstatus |
| "Haben wir genug für Black Friday?" | Agent rechnet Forecast gegen Bestand |

---

## Wo der Context Companion in der Architektur lebt

```mermaid
graph TB
    subgraph "Datenquellen (heute)"
        D1["Google Sheets\n(POs, Orders, Forecasts)"]
        D2["E-Mail\n(Lieferantenkomm.)"]
        D3["Shopify + Maya\n(Bestände, Fulfillment)"]
        D4["Asana\n(PD→SCM Übergabe)"]
        D5["Meeting-Notizen"]
    end

    subgraph "Datenquellen (morgen)"
        D6["ERP (Odoo)\n(ersetzt Sheets,\nkonsolidiert Daten)"]
    end

    subgraph "Zentrale Wissensbasis (Firestore)"
        KB["Knowledge Base"]
        CS["Kontext-Sektionen\n(kuratiert)"]
        CP["Kontext-Profile\n(pro Person)"]
    end

    subgraph "Dein Companion"
        A["AI-Agent\nmit personalisiertem\nSCM-Kontext"]
    end

    D1 --> CS
    D2 --> CS
    D3 --> CS
    D4 --> CS
    D5 --> KB
    KB -->|"AI-Kuratierung"| CS

    D6 -.->|"zukünftig"| CS

    CS --> A
    CP --> A

    style CS fill:#FF6F00,color:#fff,stroke:#FF6F00,stroke-width:3px
    style CP fill:#FF6F00,color:#fff
    style A fill:#8B5CF6,color:#fff,stroke:#8B5CF6,stroke-width:3px
    style D6 fill:#6B7280,color:#fff,stroke-dasharray:5 5
```

**Kontext-Sektionen sind quellenunabhängig.** Heute kommen die Daten aus Sheets und Mails. Wenn das ERP live geht, wechselt die Quelle — die Sektionen und Profile bleiben gleich.

---

## Diskussion

**Fragen an euch:**
- Welche der drei Szenarien spricht euch am meisten an?
- Welche täglichen Aufgaben würden am meisten von persistentem Kontext profitieren?
- In welchen Phasen des Bestellzyklus (Pre-Order, Order, Produktion, Inbound) wäre der Companion am wertvollsten?
- Sollte der Agent euch proaktiv warnen, wenn Reichweiten kritisch werden oder POs hinter Plan liegen?
