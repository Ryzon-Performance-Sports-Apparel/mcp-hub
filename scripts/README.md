# Scripts · Ryzon Knowledge Ops

Hilfsskripte für das Knowledge-Setup.

---

## `install-team-setup.sh`

**Idempotenter Installer für macOS.** Richtet das komplette Team-Setup bei Sophie, Luca, Simon oder Mario ein.

### Was es automatisch macht

1. Prüft/installiert **Homebrew**
2. Prüft/installiert **git**, **gh** (GitHub CLI)
3. GitHub-Auth + Ryzon-Org-Zugang
4. Prüft/installiert **Node.js**, **obsidian-cli**, **Obsidian.app**, **Python**
5. Fragt Nutzernamen ab (simon/sophie/luca/mario)
6. Erstellt `~/Documents/projects/context/` mit Folder-Struktur
7. Erstellt `private/<user>/` (nicht git-tracked)
8. Klont `ai-context` und `ryzon-context-vault` von Ryzon-Org
9. Legt User-Vault-Folder an, falls nicht vorhanden

### Was du NACH dem Script manuell machen musst

1. Obsidian öffnen und auf `ryzon-context-vault/<dein-name>/` zeigen
2. Claude App → Plugin hochladen (`ryzon-knowledge-ops.zip`)
3. Claude Project "Ryzon Knowledge Ops" erstellen + Instructions einfügen
4. Connectors aktivieren (GitHub + Drive)

### Usage

```bash
# Interaktiv
chmod +x install-team-setup.sh
./install-team-setup.sh

# Oder direkt von Remote (wenn als Gist/Raw verfügbar)
curl -fsSL <url>/install-team-setup.sh | bash
```

### Troubleshooting

**"Kein Zugang zur Ryzon-Org"**
→ gh auth status prüfen · ggf. `gh auth login` erneut ausführen · bei anhaltendem Problem Simon pingen für Org-Einladung

**"Konnte ryzon-context-vault nicht klonen"**
→ Repo existiert noch nicht (Simon legt es in Phase 1.2 an) · Simon nachfragen

**Script abgebrochen**
→ Script ist idempotent. Einfach nochmal starten — überspringt bereits erledigte Steps.

**Obsidian öffnet zwei Vaults**
→ Das ist OK, aber achte darauf, dass du im RICHTIGEN arbeitest (`<dein-name>/`). shared/ ist KEIN Vault.

---

## `fix-double-tags.py`

**Einmal-Script.** Fixt den area-tagger-Bug, der doppelte `tags:`-Keys in YAML-Frontmatter produziert.

### Was es macht

Scannt rekursiv nach `.md`-Files. Findet Files mit zwei `tags:`-Keys im Frontmatter, merged beide Arrays, dedupliziert, schreibt einen einzigen `tags: [...]`-Array zurück.

### Usage

```bash
# Dry-Run (default, sicher — zeigt was passieren würde)
python3 fix-double-tags.py --dry-run /pfad/zu/vault

# Apply (modifiziert Files)
python3 fix-double-tags.py --write /pfad/zu/vault

# Mehrere Folders
python3 fix-double-tags.py --write ~/Documents/projects/context/ai-context \
                                    ~/Documents/projects/context/context-vault/Granola
```

### Was das Script NICHT anfasst

- Files ohne Frontmatter
- Files mit nur einem `tags:`-Key (bereits sauber)
- Body-Content (nur Frontmatter wird geändert)

### Test vor Full-Run

```bash
# Auf 1 File testen
mkdir /tmp/tag-test && cp /pfad/eines/files.md /tmp/tag-test/
python3 fix-double-tags.py --write /tmp/tag-test
diff /pfad/eines/files.md /tmp/tag-test/files.md
```

### Safety

- Pre-Run: git commit vom betroffenen Repo, damit Rollback möglich
- Default `--dry-run` — ohne explizit `--write` keine Änderungen
- Exit-Code 1 bei Errors → sichtbar im Terminal
