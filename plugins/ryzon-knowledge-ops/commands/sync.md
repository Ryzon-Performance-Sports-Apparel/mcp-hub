---
description: "Sync local Captures + Decisions to GitHub — git pull, commit, push for both Repos. Optimized for the Code-Tab (Bash native), funktioniert auch in Cowork falls Bash dort verfügbar."
---

Der User hat `/sync` aufgerufen. Arguments: $ARGUMENTS (optional, siehe unten).

## Wofür dieser Command

Captures (`/capture`, `/decision`) schreiben **lokal**, ohne Commit. `/sync` ist der Schritt, der die Tagesarbeit auf GitHub bringt:

- `git pull --rebase` zuerst (verhindert Konflikte mit anderen Team-Members)
- `git status` prüfen — falls Changes
- Stage + commit mit synthetisierter Commit-Message basierend auf den Files
- `git push`
- Pro Repo Status reporten

## Vorbedingungen

- Du läufst in einer Umgebung mit Bash-Tool (Code-Tab in Claude-Desktop-App, oder Claude Code CLI, oder Cowork falls dort Bash freigeschaltet ist).
- Die Repos liegen unter `~/Documents/projects/context/ryzon-context-vault/` und `~/Documents/projects/context/growth-nexus/`. Falls `CONTEXT_DIR`-Override existiert, das stattdessen nutzen.
- gh-Auth ist aktiv (vom Install-Script gesetzt).

Wenn die Pfade nicht existieren oder Bash nicht verfügbar: erkläre das dem User, schlage vor das Install-Script zu re-run oder Code-Tab zu nutzen, brich ab.

## Argumente

- `/sync` (no args) — beide Repos syncen
- `/sync vault` — nur `ryzon-context-vault`
- `/sync nexus` — nur `growth-nexus`
- `/sync --dry` — zeigt nur, was geschehen würde, ohne zu committen/pushen

## Dein Vorgehen pro Repo

1. **`cd $REPO_DIR`** (entweder `ryzon-context-vault` oder `growth-nexus` je nach Argument)

2. **`git status --porcelain`** lesen. Falls leer und auch `git fetch` keine remote-changes signalisiert → Repo ist clean, weiter zum nächsten.

3. **`git pull --rebase`** zuerst.
   - Konflikt? → Stop, dem User klar erklären welche Files konflikten, vorschlagen `git rebase --abort` oder manuelles Lösen. Niemals automatisch resolven.

4. **Falls dirty** (`git status` zeigt geänderte/neue Files):
   - `git add -A` (stage alles)
   - **Commit-Message synthetisieren:**
     - Lese die geänderten/neuen `.md`-Files unter `**/*.md` (max ~20)
     - Pro File: H1-Titel oder erste Zeile extrahieren
     - Cluster nach `<author>/` Pfad-Prefix oder Type (capture/decision/etc.)
     - Format: `sync: <count> Captures + <count> Decisions (<authors>)` oder bei nur einem Eintrag: `<type>(<author>): <title>`
     - Beispiele:
       - `capture(sophie): Apollo Q2 video performance learning`
       - `sync: 3 captures + 1 decision (sophie, simon)`
   - `git commit -m "<message>"`

5. **`git push`**
   - Falls remote rejected (z.B. branch protection, oder concurrent push): pull --rebase nochmal, push retry. Max 1 Retry, dann Fehler reporten.

6. **Status-Report** sammeln pro Repo:
   - Repo-Name
   - Anzahl pulled commits (vom rebase)
   - Anzahl committed Files (oder „nichts zu committen")
   - Push-Status (✓ oder Fehler)

## Final Output

Markdown-Report wie:

```
## /sync — Status

### ryzon-context-vault
✓ Pulled: 0 changes from remote
✓ Committed: 3 files (`capture(sophie): Apollo Q2 ...`)
✓ Pushed to origin/main

### growth-nexus
✓ Pulled: 1 commit (luca's friday-retro update)
✓ Committed: 1 file (`decision(ops): CRM tool choice`)
✓ Pushed to origin/main

**Done.** Alle lokalen Änderungen sind jetzt team-weit verfügbar.
```

Falls `--dry`: gleicher Report, aber jeden Commit/Push mit `[DRY]` prefixen, und kein git-write-Command ausführen.

## Fehlerfälle

- **Kein Bash verfügbar:** Erkläre dem User, dass `/sync` Bash braucht. Empfehle Tab-Switch auf Code (Sidebar `</>`-Icon), gleicher Project-Pfad, dort `/sync` erneut.
- **Pull-Konflikt:** Stop, Files nennen, manuellen Fix vorschlagen. Nie auto-resolven.
- **Push-Reject:** einmal `git pull --rebase` retry, dann hart abbrechen mit Anleitung.
- **Repo-Pfade fehlen:** Install-Script nicht durchgelaufen — verweise auf `/wissen/growth-nexus-install`.

## Wichtig

- **Niemals ohne pull rebasen** — sonst können fremde Commits überschrieben werden.
- **Sinnvolle Commit-Messages** — sie landen im git log, sollten nachvollziehbar sein.
- **Pro Repo separat** — niemals einen kombinierten Commit über beide Repos versuchen.
- **Audit-frei für PII**: wenn ein Commit File-Pfade aus `private/` enthält → das ist ein Bug, sofort rollback (`git reset HEAD~1 --soft`) und User warnen. PII liegt außerhalb der Repos und darf nie ge-add't werden.
