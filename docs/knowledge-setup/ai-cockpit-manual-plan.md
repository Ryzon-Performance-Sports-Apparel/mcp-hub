# Interaktives Knowledge-Ops-Manual in ai-cockpit

*Plan · v1 · 2026-04-22 · Ziel: Option C vollgas, in 2 Phasen ausgeliefert*

---

## Context

Sophie und Luca (ab Mo 27.04) plus Mario (ab Woche 3) und später externer Berater brauchen einen zentralen, verständlichen Ort, um das Ryzon-Knowledge-Ops-Setup zu kapieren, zu installieren und im Alltag nachzuschlagen.

Das **ai-cockpit** (`/Users/simonheinken/Documents/projects/ai-cockpit`, Astro-SSR auf Cloud Run mit IAP + @ryzon.net SSO) ist der richtige Ort:
- Ryzon-Design, Ryzon-Authentifizierung, Ryzon-Domain
- Content-Collection-Pattern bereits etabliert (`src/content/wissen/*.mdx`)
- Bestehende `<Audience>`-Komponente für team-spezifische Inhalte
- Existierende Design-Tokens, BaseLayout, Wissens-Routing

**Output:** eine interaktive Manual-Sektion mit Hub + Sub-Pages, Download-Button für Install-Script, 4–7 custom Astro-Komponenten, kompletter Erklärung aller Commands/Schemas/Workflows.

**Non-goals:**
- Kein React/Vue-SPA — wir bleiben bei Astro Islands + Vanilla JS
- Keine Mermaid-Integration jetzt (custom SVG reicht für Phase 1)
- Kein Edit-in-Place oder User-generierter Content

---

## Gesamtarchitektur

### Content-Struktur

**Hub-Page (custom Astro):**
- `/wissen/knowledge-ops` — `src/pages/wissen/knowledge-ops.astro`
- Eigenständige Page mit Hero, Big-Picture-Diagram, Quick-Nav-Grid, Download-CTA
- Nicht im Content-Collection — ist Dashboard/Landing für Manual-Bereich

**Sub-Pages (MDX-Artikel im wissen-Collection):**

| Slug | Zweck | Primäre Komponenten |
|---|---|---|
| `knowledge-ops-install` | Step-by-Step-Install, Download, Troubleshooting | `InstallStep`, `DownloadButton` |
| `knowledge-ops-commands` | Alle 9 Slash-Commands mit Live-Beispielen | `CommandCard` |
| `knowledge-ops-schema` | 5 Dimensionen erklärt, Routing-Matrix | `DimensionMatrix` |
| `knowledge-ops-workflow` | Daily + weekly Flow, Friday-Ritual | `WorkflowDiagram` |
| `knowledge-ops-architecture` | Repo-Struktur, Vault-Layout, Claude-Project-Setup | `VaultTree` |
| `knowledge-ops-faq` | Troubleshooting, häufige Fragen, Feedback | keine custom |

**Frontmatter-Konvention für alle MDX-Artikel:**
```yaml
---
title: "..."
category: guides
date: 2026-04-25
excerpt: "..."
tags: ["knowledge-ops", "setup", ...]
audiences: ["allgemein"]   # breit, damit Sophie/Luca/Mario alle sehen
author: "Simon Heinken"
draft: false
---
```

### Navigation

Dem Hub hinzugefügt zu `src/components/Header.astro` (Navigation-Item: "Knowledge Ops"). Sub-Pages über Hub erreichbar. Alternativ: neuer Nav-Eintrag "Manual".

---

## Custom Astro-Komponenten

### Phase-1-Core (must-have, bis Fr 25.04)

#### 1. `src/components/ko/CommandCard.astro`
Expandierbarer Eintrag pro Slash-Command.

**Props:**
```typescript
{
  name: string;              // "/capture"
  category: "daily" | "periodic" | "trust" | "ritual";
  signature: string;         // "/capture <type> <content>"
  description: string;       // Kurzbeschreibung (1 Satz)
  example: string;           // Example-Eingabe
  exampleOutput?: string;    // Was der User zurückbekommt
  landingPath?: string;      // "ryzon-context-vault/<author>/<type>s/"
  agent?: string;            // "dimension-enricher"
  version: string;           // "v0.6.0"
}
```

**Verhalten:**
- Default: collapsed — zeigt Name + Signature + Description
- Click: expand → zeigt Example + Output + landing-path + Agent + Copy-Button
- Copy-Button kopiert Signature zur Clipboard
- State: `aria-expanded` + `data-expanded` (vanilla JS, kein Framework)

**Style:** Ryzon-Tokens, Card-ähnlich an bestehende `Card.astro` angelehnt.

#### 2. `src/components/ko/InstallStep.astro`
Nummerierter Install-Schritt mit copy-fähigen Code-Blocks.

**Props:**
```typescript
{
  number: number;            // 1, 2, 3, ...
  title: string;             // "Homebrew installieren"
  command?: string;          // bash command
  explanation?: string;      // Kontext / was passiert
  expectedOutput?: string;   // "Homebrew 5.1.1" etc
  troubleshooting?: string;  // optional: "falls Fehler X, ..."
}
```

**Verhalten:**
- Nummer-Badge + Titel + optionaler Copy-Command-Block
- Checkbox (`[ ]`) links — click markiert als "done", LocalStorage-persisted mit `key: ko-install-step-{n}`
- Copy-Button auf Code-Block
- Troubleshooting aufklappbar unter Haupt-Content

#### 3. `src/components/ko/DownloadButton.astro`
Prominenter Download-Link für Install-Script.

**Props:**
```typescript
{
  label: string;             // "Install-Script herunterladen"
  filename: string;          // "install-team-setup.sh"
  source: "github-raw" | "local";  // strategy
  url: string;               // die URL
  version?: string;          // "v0.6.0"
  sizeKb?: number;           // optional display
}
```

**Verhalten:**
- Großer, Ryzon-branded Button
- Click triggert Download (für github-raw: öffnet raw.githubusercontent.com)
- Zeigt Version-Badge + "immer neueste Version" Hint
- Optional: kleine Anleitung darunter ("nach Download: `chmod +x && ./...`")

**Download-Strategie:** GitHub Raw URL direkt (`https://raw.githubusercontent.com/Ryzon-Performance-Sports-Apparel/mcp-hub/main/scripts/install-team-setup.sh`). Keine lokale Kopie in `public/` — immer sync mit mcp-hub-Main.

#### 4. `src/components/ko/DimensionMatrix.astro`
Interaktive 2D-Matrix maturity × sensitivity → Landeplatz.

**Rendering:**
```
               self              team              pii
operational  [vault/<u>]      [vault/shared]   [private/]
strategic    [private/str]    [growth-nexus]*  [private/str]
```

**Verhalten:**
- Click auf Zelle → Toast/Tooltip mit: vollem Pfad, Beispielen, warum dort?
- Visual differentiation: `team + strategic` hebt sich hervor (das ist die via-Promotion-Zelle)
- Style: Grid + Hover-Zustände mit Ryzon-Tokens

### Phase-2-Advanced (Week 1, während Sophie/Luca testen)

#### 5. `src/components/ko/VaultTree.astro`
Folder-Tree-Visualisierung mit Collapsible Nodes.

**Props:** `{ user?: "simon" | "sophie" | "luca" | "mario" }` — wenn gesetzt, hebt den User-spezifischen Pfad hervor.

**Rendering:** ASCII-Tree mit klickbaren Nodes, Tooltips beim Hover (erklärt jeden Folder).

#### 6. `src/components/ko/WorkflowDiagram.astro`
Daily + weekly Flow, interaktiv. Klickbare Nodes zeigen Details.

**Technik:** Inline-SVG (hand-crafted, keine Mermaid-Dependency). Animationen via CSS-Transitions.

#### 7. `src/components/ko/TrustBatteryTracker.astro`
4-Tier-Tracker mit LocalStorage-Persistenz.

**Props:** `{ defaultLevel?: number }`
**Tiers:** 20% (Pair) · 40% (Async+Check) · 60% (Delegated+Audit) · 80%+ (Autonomous)
**Verhalten:** Slider oder Button-Pick, speichert User-Wahl in `ko-trust-battery-level`, zeigt historie (letzte 4 Werte).

---

## Pages im Detail

### Hub: `src/pages/wissen/knowledge-ops.astro`

Custom Astro-Page, **nicht** im Content-Collection (weil Dashboard-artig).

**Sektions-Layout:**
1. **Hero** — Title "Ryzon Knowledge Ops", Tagline ("Dein AI-First Wissens-Setup"), Version-Badge (v0.6.0), letzte-Update-Zeit
2. **Big-Picture-Diagramm** — Inline-SVG der Zwei-Welten-Architektur (growth-nexus ↔ ryzon-context-vault via Claude Project)
3. **Install-CTA** — prominenter `<DownloadButton>` + Link zu Install-Page
4. **Quick-Nav-Grid** — 6 Tiles zu Sub-Pages (wie auf Homepage `/index.astro` mit den Modulen, aber spezifisch für KO-Pages):
   - Commands · Schema · Workflow · Architecture · FAQ · Install
5. **Status-Footer** — Plugin-Version, Link zu GitHub-mcp-hub, "Fragen?" → Slack-Channel

**Design:** BaseLayout umschließt. Spacing und Typography konsequent über Ryzon-Tokens.

### `/wissen/knowledge-ops-install` (MDX)

**Struktur:**
1. Intro: was das Setup tut, wie lange Install dauert (~5–10 Min aktiv)
2. `<DownloadButton />` ganz oben
3. Preflight-Check (`<InstallStep number="0">`) — was du brauchst: Admin-Rechte, Ryzon-Google-Account, Claude-App-Installation
4. 10 `<InstallStep />`-Komponenten für jeden Schritt aus install-team-setup.sh
5. Post-Install-Section — manuelle Schritte (Claude Project, Plugin-Upload, Connectors) in eigenem Sub-Abschnitt
6. Troubleshooting-Section — Häufige Fehler + Lösungen

### `/wissen/knowledge-ops-commands` (MDX)

**Struktur:**
Gruppiert nach Kategorie:
- **Daily (4)**: `/capture`, `/pull`, `/decision`, `/sources` als `<CommandCard />` mit `category="daily"`
- **Periodic (3)**: `/distill`, `/find`, `/validate`
- **Trust Flagship (1)**: `/verify` — hebt sich visuell hervor (Lucas Feature)
- **Simon-only (1)**: `/promote`

Über jeder Kategorie ein 1-Absatz-Kontext: *"Diese nutzt du täglich 3–5×..."*

### `/wissen/knowledge-ops-schema` (MDX)

**Struktur:**
1. "Warum 5 Dimensionen" — 2 Absätze
2. Die 5 Felder: jede Dimension mit Werten + Wirkung (aus frontmatter-schema.md)
3. `<DimensionMatrix />` interaktiv
4. Defaults pro Type als Tabelle (aus frontmatter-schema)
5. Beispiel-Entries (Learning, Decision) als Code-Block
6. Validation-Felder-Erklärung (für `/validate`)

### `/wissen/knowledge-ops-workflow` (MDX)

**Struktur:**
1. Daily-Flow mit `<WorkflowDiagram variant="daily" />`
2. Weekly-Flow mit `<WorkflowDiagram variant="weekly" />`
3. Friday-Ritual deep-dive — vom Promotion-Reviewer-Output bis zum Retro-Ablauf
4. Trust-Battery-Konzept + `<TrustBatteryTracker />` zum selber Tracken

### `/wissen/knowledge-ops-architecture` (MDX)

**Struktur:**
1. Zwei Repos + private/ Überblick
2. `<VaultTree />` interaktiv (default: Sophie-Sicht)
3. Per-Repo-Deep-Dive (growth-nexus / ryzon-context-vault / private/)
4. Claude-Project-Setup-Guide mit Screenshot-Placeholders
5. Wie das Plugin mit Repos spricht (Connectors)

### `/wissen/knowledge-ops-faq` (MDX)

**Struktur:**
- 10–15 FAQ-Items in aufklappbaren Sections (`<details>`)
- Themen: "Was ist wenn ich PII aus Versehen committe?", "Wie öffne ich shared/ als zweiten Vault?", "Warum Sophie-Drive nicht Luca-Drive sieht", "Was mache ich wenn Install-Script abbricht?" etc.
- Contact-CTA: Slack + GitHub Issues

---

## Infrastruktur-Änderungen

### 1. Content-Schema erweitern (minor)

In `src/content.config.ts`: Tags brauchen nichts — aber wenn wir eine separate Category "knowledge-ops" wollen, hier hinzufügen. **Entscheidung:** bleib bei `category: guides`, füg Tags `["knowledge-ops", "setup"]` — macht Filter-Logik einfacher.

### 2. Header-Navigation erweitern

`src/components/Header.astro`: neuer Nav-Item "Knowledge Ops" → `/wissen/knowledge-ops`. Einzelne Zeile im Nav-Array.

### 3. Wissen-Index-Filter erweitern

`src/pages/wissen/index.astro`: die 6 Knowledge-Ops-Artikel sollen auf der Wissen-Übersicht als gruppierte Sektion auftauchen (statt nur im Filter zu erscheinen). Add einen "Knowledge Ops"-Filter-Button.

### 4. Globale Styles für KO-Components

Neue Datei `src/styles/ko-components.css` für die 7 Komponenten — wird in BaseLayout importiert (oder per-component mit scoped styles, je nach Konvention im Projekt). Check: existierende Komponenten scope'n via Astro-CSS-Scoping → selbes Pattern nutzen, keine globale CSS-Datei.

### 5. Download-URL hardcoding vs. Build-Variable

`<DownloadButton>`-Source könnte konfigurierbar sein: `RAW_BASE_URL` als Astro-Env-Variable. Für MVP: hardcoden, Refactor später.

---

## Ausliefer-Phasen

### Phase 1 — Launch-Ready (Mi 23.04 → Fr 25.04, ~12 Stunden)

**Müssen fertig sein:**
- [ ] Hub-Page `/wissen/knowledge-ops` (Layout + Hero + Quick-Nav + Download-CTA) · ~2 h
- [ ] 4 Core-Komponenten: `CommandCard`, `InstallStep`, `DownloadButton`, `DimensionMatrix` · ~4 h
- [ ] 4 MDX-Artikel: `install`, `commands`, `schema`, `faq` · ~4 h
- [ ] Header-Nav-Update · ~30 min
- [ ] Deploy + Smoke-Test · ~1 h
- [ ] Lokaler Test-Run (`npm run dev`) aller Pages + Download · ~30 min

**Deliverable:** Sophie/Luca haben beim Install-Session am Mo 27.04 eine funktionierende URL (`https://ryzon-ai.internal/wissen/knowledge-ops`), auf der sie alles nachlesen, den Install-Script runterladen und die 9 Commands mit Beispielen sehen können.

### Phase 2 — Polish (Woche 1, parallel zu Sophie/Luca-Testing, ~8–10 Stunden)

**Kommt dazu:**
- [ ] 3 Advanced-Komponenten: `VaultTree`, `WorkflowDiagram`, `TrustBatteryTracker` · ~6 h
- [ ] 2 weitere MDX-Artikel: `workflow`, `architecture` · ~2 h
- [ ] Content-Polish basierend auf Sophie/Luca-Feedback · ~1 h
- [ ] Visual Polish, Animations, A11y-Audit · ~2 h

**Deliverable:** Während Sophie/Luca in Woche 1 (28.04–02.05) aktiv testen, wächst das Manual mit ihnen. Jeder Friday-Retro (09.05) kann Content-Lücken sofort schließen.

### Phase 3 — Evolution (post-MVP, selbstständig)

**Optional ab Woche 3+:**
- Live-Preview `<CommandSimulator />` (Mock-Chat-UI)
- Changelog-Tracker aus Plugin-Repo (build-time fetch von GitHub Releases)
- Usage-Analytics (anonym, via IAP-User-Count pro Page)
- `/wissen/knowledge-ops-retros` — Public-Archiv der Friday-Retro-Notizen

---

## Deliverables-Liste (konkret)

### Phase 1 — Datei-für-Datei

| # | Typ | Pfad | Zweck |
|---|---|---|---|
| 1 | Page | `ai-cockpit/src/pages/wissen/knowledge-ops.astro` | Hub |
| 2 | Component | `ai-cockpit/src/components/ko/CommandCard.astro` | Command-Doc |
| 3 | Component | `ai-cockpit/src/components/ko/InstallStep.astro` | Install-Schritt |
| 4 | Component | `ai-cockpit/src/components/ko/DownloadButton.astro` | Script-Download |
| 5 | Component | `ai-cockpit/src/components/ko/DimensionMatrix.astro` | Schema-Matrix |
| 6 | MDX | `ai-cockpit/src/content/wissen/knowledge-ops-install.mdx` | Install-Guide |
| 7 | MDX | `ai-cockpit/src/content/wissen/knowledge-ops-commands.mdx` | Commands |
| 8 | MDX | `ai-cockpit/src/content/wissen/knowledge-ops-schema.mdx` | Schema |
| 9 | MDX | `ai-cockpit/src/content/wissen/knowledge-ops-faq.mdx` | FAQ |
| 10 | Modify | `ai-cockpit/src/components/Header.astro` | Nav-Item |

### Phase 2 — Datei-für-Datei

| # | Typ | Pfad |
|---|---|---|
| 11 | Component | `ai-cockpit/src/components/ko/VaultTree.astro` |
| 12 | Component | `ai-cockpit/src/components/ko/WorkflowDiagram.astro` |
| 13 | Component | `ai-cockpit/src/components/ko/TrustBatteryTracker.astro` |
| 14 | MDX | `ai-cockpit/src/content/wissen/knowledge-ops-workflow.mdx` |
| 15 | MDX | `ai-cockpit/src/content/wissen/knowledge-ops-architecture.mdx` |

---

## Critical Files zum Reusen (keine Neu-Erfindung)

Vor dem Bauen:

1. `ai-cockpit/src/content.config.ts` — Zod-Schema, Audience-Enum — wir ergänzen nichts, nur nutzen
2. `ai-cockpit/src/layouts/BaseLayout.astro` — wraps all pages — einfach importieren
3. `ai-cockpit/src/components/Card.astro` — Style-Vorlage für CommandCard
4. `ai-cockpit/src/components/article/Audience.astro` — Muster für Vanilla-JS-Interaktivität (collapse/expand)
5. `ai-cockpit/src/pages/index.astro` — Modul-Grid-Pattern für die Hub-Page Quick-Nav
6. `ai-cockpit/src/pages/wissen/[slug].astro` — MDX-Rendering-Pattern, Frontmatter-Handling
7. `ai-cockpit/src/styles/ryzon-tokens.css` — alle Farben/Spacings/Radien kommen hier raus
8. `ai-cockpit/src/content/wissen/mcp-101.mdx` — gutes Vorlage-MDX-Artikel
9. `mcp-hub/docs/knowledge-setup/team-readme.md` — Content-Quelle für MDX-Artikel
10. `mcp-hub/docs/knowledge-setup/meeting-agenda-sophie-luca.md` — Diagramm-Referenz

---

## Verification

### Phase 1 Verification (bis Fr 25.04)

**Build & Deploy:**
- [ ] `npm run build` in ai-cockpit ohne Errors
- [ ] `npm run preview` — alle 5 Pages rendern (Hub + 4 MDX)
- [ ] Deploy auf Cloud Run erfolgreich (GitHub Actions)
- [ ] IAP-SSO funktioniert (Login als @ryzon.net-User sichtbar)

**Funktional:**
- [ ] Hub lädt in <2s
- [ ] DownloadButton führt zu raw.githubusercontent.com/.../install-team-setup.sh und startet Download
- [ ] CommandCard expand/collapse funktioniert, Copy-Button kopiert Signature
- [ ] InstallStep-Checkboxen persistieren in LocalStorage (nach Reload wieder markiert)
- [ ] DimensionMatrix-Clicks zeigen Tooltips
- [ ] Alle internen Links auflösen (keine 404)
- [ ] MDX-Artikel rendern korrekt mit Audience-Komponenten

**Content-Qualität:**
- [ ] Sophie/Luca kann Manual in <15 Min kompletten Überblick bekommen
- [ ] Install-Guide ist vollständig (alle 10 Steps aus install-team-setup.sh dokumentiert)
- [ ] Jeder der 9 Commands hat: Signature, Description, Example, Landing-Path
- [ ] FAQ deckt mindestens die 10 wichtigsten Fragen ab

### Phase 2 Verification (Ende Woche 1)

- [ ] VaultTree rendert für alle 4 User-Perspektiven
- [ ] WorkflowDiagram animiert sauber, click-responsive
- [ ] TrustBatteryTracker persistiert über Sessions
- [ ] Workflow + Architecture MDX vollständig
- [ ] A11y: Tab-Navigation, ARIA-Labels, Kontrast-Check passing

### Post-Launch Verification (Fr 09.05, 1. Friday-Retro)

- [ ] Sophie/Luca haben Manual-Seite mindestens 5× besucht (IAP-Logs)
- [ ] Feedback-Items aus Retro in Content eingearbeitet
- [ ] Keine Downtime / Deploy-Fehler

---

## Risiken & Offene Punkte

- **Mermaid-Deferral-Risiko:** WorkflowDiagram als Custom-SVG baut Simon manuell — wenn's zu komplex wird, fällt wir auf Mermaid zurück (30 min Setup)
- **GitHub-Raw-URL-Race:** wenn mcp-hub-main branch kurz vor Install-Session gepusht wird, Cache-Probleme möglich. Mitigation: Download-Button zeigt Version + lädt mit `?v=0.6.0` als Cache-Buster
- **IAP-Access-Latenz:** neue Pages auf Cloud Run können 30–60s warm-up brauchen. Für Install-Session unkritisch
- **Content-Sync mit mcp-hub:** MDX-Artikel und team-readme.md können auseinanderdriften. Mitigation: MDX-Artikel referenzieren mcp-hub-Docs als "tiefer Link", duplizieren nicht im Detail
- **LocalStorage-Konflikte:** InstallStep + TrustBatteryTracker teilen User-Browser — eindeutige Prefix `ko-*` für alle Keys

---

## Offene Fragen vor dem Bauen

1. **Nav-Platzierung:** "Knowledge Ops" als Top-Level-Nav-Item in Header, oder als Sub unter "Wissen"? Vorschlag: Top-Level, damit Sophie/Luca direkt sehen.
2. **Hub-URL:** `/wissen/knowledge-ops` (in Wissen-Subtree) oder `/knowledge-ops` (Top-Level)? Vorschlag: `/wissen/knowledge-ops` für Konsistenz mit bestehenden Wissen-Artikeln.
3. **Download-Strategie:** raw.githubusercontent.com-Link oder Build-time-Fetch in public/? Vorschlag: raw-URL mit Version-Badge.
4. **Content-Duplikation:** vollständig detaillierte MDX-Artikel, oder dünne Einführungen + "Details siehe GitHub-Docs"-Links? Vorschlag: vollständig für User-Facing (sie sollen nicht ins GitHub wechseln müssen), GitHub-Docs bleibt Quelle für Dev.
5. **Audience-Scoping:** alle KO-Artikel mit `audiences: ["allgemein"]` (sichtbar für alle), oder spezifischer pro Team?

---

## Timeline-Zusammenfassung

| Termin | Meilenstein |
|---|---|
| **Mi 23.04** | Hub-Page + 4 Core-Components gebaut |
| **Do 24.04** | 4 MDX-Artikel fertig |
| **Fr 25.04** | Deploy, Smoke-Test, Phase 1 fertig |
| **Mo 27.04** | Install-Session mit Sophie/Luca — zeigen Manual live |
| **Di–Do 28.04–30.04** | Phase 2 nebenher: 3 Advanced-Components + 2 MDX |
| **Fr 09.05** | 1. Friday-Retro: Feedback in Content einarbeiten |
| **Mo 12.05+** | Mario-Onboarding via Manual-URL — Material ausgereift |

---

## Zeitschätzung

- **Phase 1:** ~12 Stunden Simon-Zeit (oder meine Zeit mit Claude-Code-Autopilot)
- **Phase 2:** ~8–10 Stunden verteilt über Woche 1
- **Total MVP:** ~20 Stunden

Machbar bis Mo 27.04 bei ~3 Stunden pro Tag ab morgen.
