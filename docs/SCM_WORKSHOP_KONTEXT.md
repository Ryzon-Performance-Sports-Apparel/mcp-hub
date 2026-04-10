# Ryzon Supply Chain Management — Workshop-Kontext

**Erstellt:** 10. April 2026
**Zweck:** Kontext-Dokument für Workshop-Vorbereitung — alle bekannten SCM-relevanten Themen konsolidiert

---

## 1. Fertigungsmodell

### FOB / Full Package (~90% der Bestellungen)
- Konfektionär (Tier 1) beschafft alle Materialien selbst und liefert fertiges Produkt
- **Besonderheit:** Ryzon nominiert trotzdem alle Materialien aktiv und pflegt direkte Beziehungen zu ~30 Tier-2-Lieferanten
- Forecasts werden an Tier-2-Lieferanten übermittelt — Ryzon greift tief in die Lieferkette ein, auch wenn der Materialkauf formal beim Konfektionär liegt
- → Eine PO an Konfektionär (Tier 1)

### CMT / Lohnveredelung (~10% — strategisch: Ausstieg geplant)
- Ryzon beschafft Hauptstoffe selbst und stellt sie dem Konfektionär bei
- Ryzon bleibt Materialeigentümer während des gesamten Prozesses
- Kleinere Trims (Reißverschlüsse, Transferdrucke) werden nur nominiert, nicht selbst beschafft
- Materialfluss: Tier-2-Lieferant liefert Stoff direkt zum Konfektionär (kein physischer Zwischenstopp bei Ryzon)
- → Zwei separate POs: PO A → Stofflieferant (Tier 2), PO B → Konfektionär (Tier 1)
- 1–5 Lohnfertigungsaufträge pro Monat mit saisonalen Schwankungen

### Strategische Richtung
Ryzon plant, das CMT-Modell mittelfristig vollständig aufzugeben und auf FOB umzustellen.

---

## 2. Lieferanten-Tier-Struktur

```
Tier 3: Rohmaterialien (Garne, Basischemikalien)
  │  Begrenzter direkter Kontakt — über Tier 2 gesteuert
  ▼
Tier 2: Komponenten (Stoffe, Reißverschlüsse, Pads, Prints, Labels)
  │  Hauptinnovationsort bei Ryzon — engste Lieferantenbeziehung
  │  ~30 Lieferanten
  ▼
Tier 1: Konfektionäre / Assembly (Cut, Sew, Pack)
  │  ~15 Lohnfertiger (bis zu 10 regelmäßig aktiv)
  │  z.B. Petratex (Petrabook), Stamperia Alicese (MS Dynamics), LTP, Utenos
  ▼
Active Ants (3PL) → Endkunde
```

### Lieferanten-ERPs (bekannt)
- Petratex: Petrabook
- Stamperia Alicese: vermutlich MS Dynamics
- LTP / Utenos: unbekannt

---

## 3. Beschaffungsprozess (P2P-1 — dokumentiert, Entwurf v1.0)

### Prozess-Steckbrief
- **Owner:** Andreas Peters (SCM Lead)
- **Entscheider Bestellmenge:** Andreas Peters, Laura oder Max
- **Auslöser:** Fester Bestellrhythmus (z.B. quartalsweise) — nicht Tool-getriggert
- **SKU-Anzahl:** 5.000+ SKUs gesamt, davon 2.000–3.000 aktiv nachbestellrelevant

### Prozessschritte
1. **Bedarfsermittlung & Mengenentscheidung** — Manuell, kein automatischer Vorschlag
2. **Mengenbasierte Preisverhandlung** — Vor PO-Erstellung, nicht zentral dokumentiert
3. **PO-Erstellung** — Google Sheets/Excel, manuelles Template
4. **Freigabe** — Ab Schwellenwert durch Andi (Teamlead SCM); Schwellenwert nicht klar definiert
5. **PO-Übermittlung** — Per E-Mail direkt aus PO-Sheet (kein Portal, kein EDI)
6. **Lieferantenbestätigung** — Per E-Mail, manuell in Google Sheet eingetragen
7. **Materialbeistellung (nur CMT)** — Tier 2 liefert direkt an Tier 1, Ryzon koordiniert
8. **Produktionsmonitoring** — Eher reaktiv (bei Nachfrage oder Verzögerung)
9. **Versandorganisation** — SCM organisiert (Incoterms, Kurier vs. Spedition)

### Aktuelle Systeme im Beschaffungsprozess
| System | Rolle |
|--------|-------|
| Google Sheets / Excel | PO-Erstellung, Lieferantenbestätigung, Lieferterminliste |
| Google Sheet "fortlaufende Order" | Laufende Bestellübersicht |
| Google Sheet "BP Supplier" | Schnittstelle zum Finance-Team |
| E-Mail | PO-Übermittlung, Lieferantenbestätigung |
| Asana | Upstream-Trigger (PD→SCM Übergabe), kein Downstream-Tracking |
| Maya (Active Ants) | Wareneingang (manuell durch Christo) |
| Inventory Planner | Bedarfsprognose (nur Shopify-Daten) |

---

## 4. Inbound & Wareneingang (P2P-2 — nicht dokumentiert)

- Christo gibt Daten manuell in Maya (Active Ants ERP) für jede Eingangslieferung ein
- Kein automatischer Prozess zwischen Lieferant → Active Ants
- Lieferavisierung und Wareneingang noch nicht formal erfasst
- Kein SKU-Level-Tracking (Bestellung vs. tatsächliche Lieferung)

---

## 5. Bestandsbewertung & Landed Costs (P2P-3 — nicht dokumentiert)

- Bestandsbewertungsmethode: Weighted Average Cost (primär), FIFO und Specific Cost als Anforderung
- Landed Costs: Transport-/Inbound-Kosten müssen auf Artikelpreise verteilt werden
- Verteilungsoptionen: nach Menge, Kosten, Gewicht oder Volumen
- Aktuell kein System für automatische Bestandsbewertung oder Landed-Cost-Zuordnung

---

## 6. Rechnungsprüfung & Zahlung (P2P-4 — nicht dokumentiert)

- Kein Three-Way-Match möglich (PO ↔ Wareneingang ↔ Rechnung)
- Manuelle Rechnungsprüfung, dauert ~3 Tage pro Order
- Agicap für Liquiditätsmanagement, OCR, Rechnungsprüfung
- Google Sheet "BP Supplier" als Schnittstelle zum Finance-Team — manuell gepflegt

---

## 7. Forecasting & Demand Planning

### IST-Zustand (komplett manuell, fragmentiert)

**Inputs:**
- Shopify Analytics (Saisonalität, Verkaufsdaten)
- Inventory Planner (Bestandshistorie, verlorene Verkäufe — nur Shopify-Daten)
- Looker Studio Product KPI Board (Varianten-Performance, Farbbeliebtheit, Retourenquoten)
- Margin List (Stammdaten-Spreadsheet)

**Forecast-Prozess:**
Styles filtern → aktive Styles identifizieren → Demand analysieren → Growth Projection addieren

**Strukturelle Lücken:**
- BOMs nicht mit Fertigprodukten verknüpft → Komponentenbedarf nicht prognostizierbar
- Produktgenerationen nicht verknüpft → kein automatischer YoY-Vergleich
- Keine Rabatthistorie → Promotion-Impact-Analyse unmöglich
- Keine komponentenbasierte Bedarfsplanung (Tier-2-Bedarf nicht ableitbar)
- Inventory Planner kennt keinen PIM-Status, keine PLM-Daten

### SOLL-Zustand
ERP liefert integrierte Demand Planning mit: Sales Velocity, Bestandsniveaus, Lead Times, Komponenten-BOMs und saisonalen Mustern.

---

## 8. Fulfillment & 3PL

### Active Ants (aktueller 3PL)
- Eigenentwickeltes ERP: Maya
- Chaotische Lagerführung
- Shopify → Active Ants: Direkter Webhook (keine Middleware)
- ID-Mapping: Shopify Order Number = Maya External Order Number
- Teillieferungen möglich
- Bestandssync: Maya → Shopify, sofortig bei Anpassungen
- Shopify ist Source of Truth für Inventory (Active Ants Ausnahme: 1 Min Delay)
- Stündlicher Sync von Maßen/Gewichten: Maya → Airtable PIM (100 SKUs/Batch)
- Customs-Daten (HTS, Ursprungsland) werden von PIM → Maya gepusht

### Zweiter 3PL in USA geplant
- Intercompany: Automatisches Routing basierend auf Verfügbarkeit geplant
- Cross-Border Fulfillment: US-Orders aus DE-Bestand wenn US nicht verfügbar

### EasyScan
- Für Ein-/Auslagerung bei Stores

### Volumen-Kennzahlen
| Metrik | Wert |
|--------|------|
| Orders/Monat (normal) | ~25.000–30.000 |
| Orders/Monat (Peak) | ~50.000 |
| Peak Day (Black Friday) | 50.000 Orders |
| Peak Minute | ~10.000 Orders |
| Target Peak Day Capacity | 100.000 Orders |
| Inventory Sync Delay | ~4 Sekunden (Shopify ↔ Active Ants) |

### Black Friday Strategie
- Shop → 3PL Verbindung bleibt direkt bestehen
- ERP wird nachgelagert angebunden (kein Bottleneck im Peak)

---

## 9. Retouren & Returns

- Trusted Returns als Retourenportal (QR-Code basiert)
- Matrixify für Bulk Export/Import bei Retourenerstattung
- Kostenloser Repair-Service mit Statusverfolgung
- Kein Self-Service-Stornierung für Kunden (nur durch Customer Service, solange kein Versandlabel erstellt)
- GoKarla für Tracking-Benachrichtigungen

---

## 10. Übergabe Produktentwicklung → SCM

### Mechanismus
- Übergabe via Asana-Task mit 13 standardisierten Subtasks pro Produkt
- PD-Verantwortung endet bei Prototyp-Freigabe ("marktreifes Produkt")
- Team-Trennung seit Dez 2024: PD (Idee → Marktreifes Produkt) vs. SCM (Bestellung → Lieferung)

### Rollenboard: 10 SCM-relevante Phasen (Phasen 6–10)

**Phase 6 — Pre-Order Prozess** (Owner: Andi)
- Forecast T1 (Andi, Max), Forecast T2, Fabric Order (Max)
- Preisverhandlung Produkt (Konstantin) / SC (Andi)
- Quarterly Based: Forecast Nilorn für Packaging Materials (Joost, Max)
- Mengenplanung Collabs (Max)

**Phase 7 — Order Prozess** (Owner: Andi)
- Farbkonkretisierung (Maria)
- Ordersheet & Sticker File (Max)
- Mengenplanung Style (Andi) / SKU (Max)
- Ordertechsheets & BOM (Joost, Elisabeth, Isa)
- Supply Chain Administration (Max, Amelie)
- Fabric Farbeinteilung (Max, Maria)
- Marketing Sample Order (Joost)

**Phase 8 — Produktion**
- Qualitatives Monitoring (Elisabeth, Joost)
- Zeitliches Monitoring (Max)
- Monitoring Foto Sampleorder & interne Weitergabe (Joost)
- Fortlaufende Kommunikation mit Produzenten (Lisa)

**Phase 9 — Markteinführung & Verkauf**
- Produktinformationen (Elisabeth, Joost, Lisa)
- Kollektionsübersicht & Farbkombinationen Design (Maria/Elena)
- Sold out suggestions Shopify (Joost)
- Restock Info Website (Max)
- Verkaufspreise (Andi), Rabatte (Andi)
- Internes Wissensmanagement (Elisabeth, Joost, Konstantin)
- Replenishment (Max, Amelie)

**Phase 10 — Post-Sell**
- Help Customer Service & Feedback kanalisieren (Elisabeth, Konstantin)

---

## 11. SCM-Team & Verantwortlichkeiten

| Person | Fokus |
|--------|-------|
| Andreas Peters (Andi) | SCM Lead, Bedarfsplanung, Mengenplanung-Style, Preisverhandlung SC, Supplier Selection |
| Max (Maximilian Gnann) | Mengenplanung-SKU, Fabric Order, POS-Compliance, Replenishment |
| Laura | Supplier Selection & Risk Management, Demand Planning & Purchasing |
| Amelie | Supply Chain Administration, Replenishment |
| Daria | Orderplanung, PO Sheets, Sticker Info |
| Tina | Robosize, Retraced |
| Christo | Maya-Dateneingabe bei Wareneingang, PIM-Datenpflege |

---

## 12. Supply Chain Transparenz & Compliance

- **Retraced:** Tool für Supply Chain Transparenz
- **Compliance & Contract Management:** Noch nicht dokumentiert (Asana: Prozess 5.4)
- **Sourcing & Pricing Strategy:** Noch nicht dokumentiert (Asana: Prozess 5.2)
- **Supplier Selection & Risk Management:** Noch nicht dokumentiert (Asana: Prozess 5.1)

---

## 13. Systeme im SCM-Kontext (Gesamtüberblick)

| System | Rolle | Pain Point |
|--------|-------|-----------|
| Google Sheets / Excel | PO-Erstellung, Forecasting, Lieferterminliste, Orderliste | Manuell, fehleranfällig, kein SKU-Tracking |
| Asana | Upstream-Trigger PD→SCM, 13 Subtasks/Produkt | Kein Downstream-Tracking |
| Maya (Active Ants) | Wareneingang, Fulfillment, Bestandsführung | Manuelle Dateneingabe durch Christo |
| Inventory Planner | Bedarfsprognose | Nur Shopify-Daten, keine PLM-Integration |
| Shopify Plus | Bestellannahme, Inventory SoT | 4-Sek Sync Delay, keine Reservierung |
| Airtable PIM | Produktdatenpflege, Stock-Tabelle | PIM-Bypass bei Content |
| Agicap | Liquiditätsmanagement, OCR | — |
| Retraced | Supply Chain Transparenz | — |
| E-Mail | PO-Übermittlung, Lieferantenkommunikation | Kein strukturierter Datenaustausch |

---

## 14. Bekannte Pain Points (konsolidiert)

### Operative Pain Points
- **Kein SKU-Level-Tracking** für Bestellungen vs. Lieferungen
- **Kein Three-Way-Match** (PO ↔ Wareneingang ↔ Rechnung) — Rechnungsprüfung dauert ~3 Tage/Order
- **Copy-Paste zwischen Systemen** — Asana → Airtable PIM → Shopify, alles manuell
- **Manuelle PO-Erstellung** in Google Sheets ohne Validierung
- **Kein automatischer Bestellvorschlag** — Inventory Planner wird nicht als Trigger genutzt
- **Manueller Wareneingang** — Christo gibt jeden Eingang einzeln in Maya ein
- **Keine Bestandsreservierung** außerhalb von Shopify
- **4-Sekunden Inventory-Sync-Verzögerung** — Überverkaufsrisiko bei Peaks
- **Preisdokumentation nicht zentral** — Verhandlungsergebnisse in PO-Sheets oder E-Mail-Anhängen

### Strukturelle Pain Points
- **BOMs nicht mit Fertigprodukten verknüpft** → Komponentenbedarf nicht prognostizierbar
- **Produktgenerationen nicht verknüpft** → kein YoY-Vergleich möglich
- **Keine Rabatthistorie** → Promotion-Impact-Analyse unmöglich
- **Fragmentierter Datenfluss** zwischen Figma, Asana, Google Docs, PDFs, Excel, E-Mail, Post
- **Single Points of Failure** — Eine Person pro Prozess, keine Dokumentation
- **Freigabe-Schwellenwert nicht definiert** — Ab wann braucht eine PO Andi's Freigabe?

### Skalierbarkeits-Pain Points
- Team-Kapazität wird durch operative Tasks aufgefressen
- Strategische Arbeit in Hochphasen deprioritisiert
- Kathi 80% verfügbar, blockiert durch Orderphasen (Winter: Dez-Feb, Spring/Summer: Jun-Aug)

---

## 15. ERP-Anforderungen aus SCM-Sicht

### Must-Haves (aus ERP-Discovery-Sessions)
- Subcontracting / Lohnveredelung (CMT-Modell abbilden, auch wenn Ausstieg geplant)
- Materialbeistellung und Konsignationslager-Tracking
- Three-Way-Match (PO ↔ Wareneingang ↔ Rechnung)
- Landed Costs Verteilung
- Multi-Entity / Multi-Country (DE, US, perspektivisch AT, CH)
- Intercompany-Transfers mit automatischem Routing
- Bestandsreservierung bei Auftragsbestätigung
- Shopify-Integration (bidirektional)
- 3PL-Integration (Active Ants + US-3PL)
- Black Friday Peak Handling (100.000+ Orders/Tag)

### Erkenntnisse aus Vendor Demos
- **Odoo:** Subcontracting mit Standard-Stücklisten, Rahmenverträge, Landed Costs nach Menge/Kosten/Gewicht/Volumen, 90% Standardkonformität
- **NetSuite:** Höchste Funktionsabdeckung (98.5%), Intercompany-Automatisierung, nachgelagerte ERP-Anbindung bei Peak
- **Xentral:** 53% Standard-Abdeckung (niedrigste), Multi-Mandanten über 2 Instanzen
- **Dynamics SCM:** Multi-Country-Support, PLM-Modul als Add-on, aber hohe Komplexität

---

## 16. Offene Fragen für Workshop

- [ ] Freigabe-Schwellenwert für POs — ab welchem Betrag? Gibt es eine Eskalationsstufe oberhalb von Andi?
- [ ] Post-Ordering-Prozess im Detail (zwischen PO-Versand und Wareneingang)
- [ ] Active Ants Integration: Wie sieht der Inbound-Prozess genau aus?
- [ ] US-3PL: Welcher Anbieter? Wie sieht die Integration aus?
- [ ] CMT-Ausstieg: Timeline? Welche Lieferanten sind noch auf CMT?
- [ ] Sourcing-Strategie: Wie werden neue Lieferanten evaluiert und ongeboardet?
- [ ] Compliance/Retraced: Welche Daten fließen, wie wird's genutzt?
- [ ] Demand Planning: Wer macht den Forecast konkret, und wie fließen die Ergebnisse in POs?
- [ ] Intercompany-Routing: Regeln für Cross-Border Fulfillment?
- [ ] Backorder/Pre-Order: Aktuell nicht möglich — ist das geplant?

---

## 17. Datenarchitektur-Kontext

```
PLM (Master: Produkt-Design-Daten)
  → Tech Packs, BOMs, Specs, Sampling
  → Übergabepunkt: Production Release
      ↓
ERP (Master: operative Daten)
  → Inventory, Kosten, Orders, Fulfillment
  → Shopify bleibt Inventory SoT (Active Ants Ausnahme)
      ↓
Shopify (Storefront + Bestellannahme)
  → Kein direkter PLM-Shopify-Sync
```

**Bestätigte Architektur-Richtung:** PLM → ERP → Shopify
