# Dein Companion in Aktion

> Vom Session-Start bis zur smarten Antwort — wie der personalisierte Agent im Alltag funktioniert.

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
    Auth-->>Agent: lisa@ryzon.net

    Agent->>Profil: Profil für Lisa laden
    Profil-->>Agent: Rolle: Performance Marketer<br/>Primär: Performance, Zielgruppen, Creatives<br/>Unterstützend: Produkte, Märkte

    Agent->>Sektionen: Primäre Sektionen laden
    Sektionen-->>Agent: Campaign Performance (aktuell)<br/>Ryzon Zielgruppen (aktuell)<br/>Creative Learnings (aktuell)

    Agent->>Sektionen: Unterstützende Sektionen laden
    Sektionen-->>Agent: Produktlinien (kompakt)<br/>Markt-Besonderheiten (kompakt)

    Note over Agent: Kontext zusammenbauen:<br/>Primär = "Dein wichtigster Kontext"<br/>Unterstützend = "Zusätzlicher Kontext"<br/>Hintergrund = "Bei Bedarf verfügbar"

    Agent-->>Du: Bereit! 🟢<br/>"Ich kenne deine aktuellen Kampagnen,<br/>Zielgruppen und Creative Learnings."
```

**Das passiert in Sekunden, automatisch, bei jedem Session-Start.** Kein Copy-Paste, kein Briefing. Du startest und der Agent weiß Bescheid.

---

## Konkretes Szenario: Triathlon-Kampagne DACH

### Die Aufgabe

> **Du:** Erstelle eine neue Conversion-Kampagne für die Triathlon-Linie im DACH-Markt.

### Was der Agent bereits weiß (nach Profil-Stufe)

```mermaid
graph TB
    subgraph "Primär — denkt der Agent sofort mit"
        P1["Campaign Performance\n• DACH Triathlon: 3.2x ROAS (Catalog)\n• Video outperformt Image um 40%\n• Top-Performer: 'Tri Suit Launch' 4.8x ROAS"]
        P2["Zielgruppen\n• Triathlon-Persona: 28–45, Ausdauer,\n  HH >60k, technik-affin\n• DACH-Fokus, US wachsend"]
        P3["Creative Learnings\n• Video > Image für Triathlon\n• UGC hat 2x CTR vs. Studio\n• Carousel für Cross-Selling"]
    end

    subgraph "Unterstützend — zieht der Agent dazu"
        S1["Produktlinien\n• Tri Suit 2026: Launch 15. Mai\n• Recyceltes Material, 12% leichter\n• Preis: 249 EUR"]
        S2["Märkte\n• CH: Separate Ad Sets (DE/FR/IT)\n• DE: Preisangabenverordnung bei Sale"]
    end

    subgraph "Hintergrund — auf Nachfrage"
        B1["Brand Voice: premium, clean..."]
        B2["Events: IRONMAN Hamburg 25.5..."]
    end

    style P1 fill:#10B981,color:#fff
    style P2 fill:#10B981,color:#fff
    style P3 fill:#10B981,color:#fff
    style S1 fill:#3B82F6,color:#fff
    style S2 fill:#3B82F6,color:#fff
    style B1 fill:#6B7280,color:#fff
    style B2 fill:#6B7280,color:#fff
```

### Die Antwort des Agents

> **Agent:** Basierend auf euren aktuellen Daten empfehle ich:
>
> **Kampagnenstruktur:**
> - Catalog-Kampagne (3.2x ROAS historisch im Triathlon-Segment)
> - Separate Ad Sets für DE, AT und CH (CH mit DE/FR-Varianten)
>
> **Zielgruppe:**
> - Triathlon-Persona: 28–45, Ausdauersportler, HH >60k
> - Lookalike basierend auf Top 5% Käufern der Triathlon-Linie
>
> **Creative-Empfehlung:**
> - Video als Lead-Format (40% besser als Image in diesem Segment)
> - UGC-Style bevorzugt (2x CTR)
> - Tri Suit 2026 als Hero-Produkt (Launch 15. Mai — Timing passt perfekt)
>
> **Budget-Orientierung:**
> - Basierend auf dem aktuellen Spend-Trend (+15% MoM) und einem Target-ROAS von 3x
>
> Soll ich die Kampagne so im Meta Ads Manager anlegen?

**Ohne ein einziges Wort Kontext von dir.** Alles kam aus den Sektionen, priorisiert nach deinem Profil.

---

## Was das im Alltag bedeutet

| Heute | Mit Context Companion |
|-------|----------------------|
| "Moment, ich kopiere dir die Zielgruppen rein..." | Agent kennt die Zielgruppen bereits |
| "Schau mal in den Ads Manager, was gerade performt" | Agent hat aktuelle Performance-Daten |
| "Der Ton sollte eher so wie..." | Agent kennt die Brand Voice |
| "Vergiss nicht, für CH brauchen wir..." | Agent weiß über Markt-Besonderheiten Bescheid |
| "Nächsten Monat launcht übrigens..." | Agent kennt den Launch-Kalender |

---

## Wo der Context Companion in der Architektur lebt

```mermaid
graph TB
    subgraph "Datenquellen"
        D1["Google Drive"]
        D2["Granola Notes"]
        D3["Meta Ads API"]
        D4["Manuelle Pflege"]
    end

    subgraph "Zentrale Wissensbasis (Firestore)"
        KB["Knowledge Base\n(Rohdaten)"]
        CS["Kontext-Sektionen\n(kuratiert)"]
        CP["Kontext-Profile\n(pro Person)"]
        AC["Zugangskontrolle\n(Policies)"]
    end

    subgraph "MCP Server"
        M1["Meta Ads MCP\n(36 Tools)"]
        M2["Knowledge MCP\n(Suche + Kontext)"]
    end

    subgraph "Dein Companion"
        A["AI-Agent\nmit personalisiertem Kontext"]
    end

    D1 --> KB
    D2 --> KB
    D3 --> CS
    D4 --> CS
    KB -->|"AI-Kuratierung"| CS
    CS --> M2
    CP --> M2
    AC --> M2
    M1 --> A
    M2 -->|"Profil + Sektionen"| A

    style CS fill:#FF6F00,color:#fff,stroke:#FF6F00,stroke-width:3px
    style CP fill:#FF6F00,color:#fff
    style A fill:#8B5CF6,color:#fff,stroke:#8B5CF6,stroke-width:3px
    style KB fill:#F59E0B,color:#fff
```

**Kontext-Sektionen und Profile** sind eine neue Schicht in der bestehenden Firestore-Infrastruktur. Sie bauen auf der Knowledge Base auf und werden über den gleichen MCP-Server ausgeliefert — kein neues System, sondern eine Erweiterung.

---

## Diskussion

**Fragen an euch:**
- Welche täglichen Aufgaben würden am meisten von persistentem Kontext profitieren?
- Gibt es Situationen, in denen ihr euer Profil temporär anpassen wollen würdet? (z.B. während eines Produkt-Launches die Produktlinien-Sektion auf "Primär" setzen)
- Sollte der Agent euch am Anfang sagen, welchen Kontext er geladen hat — oder soll das unsichtbar im Hintergrund passieren?
