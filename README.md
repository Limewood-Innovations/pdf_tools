# PDF Tools (Windows)

Kleines Projekt zum Splitten eines gescannten PDF-Stapels in 2-Seiten-PDFs und optionalem Entfernen von Leerseiten.

## Inhalt
- `pdf_batch_tools.py` – Hauptskript (Python)
- `run_split.bat` – Batch zum Start per Doppelklick
- `watch-and-run.ps1` – PowerShell-Watcher, startet automatisch bei neuen PDFs
- `setup_venv.ps1` – Einmalige Einrichtung (virtuelle Umgebung + Abhängigkeiten)
- `requirements.txt` – Python-Abhängigkeiten (pypdf)
- `copy-sharepoint-to-local.ps1` – Dateien aus SharePoint Online in ein lokales/UNC-Verzeichnis kopieren
  
Standardordner (im Projektverzeichnis):
- `01_input` – Eingang (zu verarbeitende PDFs)
- `02_processed` – gesplittete Ausgaben
- `03_cleand` – bereinigte Ausgaben (ohne Leerseiten)
- `99_archived` – optionales Archiv (manuell/extern nutzbar)

## Schnellstart (Windows Server / Desktop)

1. Projekt an beliebigen Ort entpacken/klonen.
2. Python 3.12 installieren (mit "Add to PATH").
3. PowerShell im Projektordner öffnen und ausführen:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\setup_venv.ps1
   ```
4. Lege deine gescannte PDF in `01_input`.
5. Starte:
   - per Doppelklick `run_split.bat` (arbeitet auf 01_input → 02_processed/03_cleand) **oder**
   - Watcher: `powershell -File .\watch-and-run.ps1`

Ausgabe liegt in `02_processed` (gesplittet) und `03_cleand` (optional bereinigt).

## Manuelle Nutzung
```powershell
# Aktivieren der venv
.\.venv\Scripts\Activate.ps1

# Splitten + Clean (im Projektordner) + Originale archivieren
python .\pdf_batch_tools.py --in-dir .\01_input --out-dir-split .\02_processed --out-dir-clean .\03_cleand --archive-dir .\99_archived

# Nur splitten
python .\pdf_batch_tools.py --in-dir .\01_input --out-dir-split .\02_processed --no-clean

# Gut funktionierender split Befehl für gescannte Dokumente
python  pdf_batch_tools.py --in-dir ./01_input --out-dir-split ./02_processed --out-dir-clean ./03_cleaned --debug-pages --min-alnum-ratio 0.2 --no-image-nonblank --min-bytes 6000 --log-file ./logs/pdf.log
```

## Aufgabenplaner (Task Scheduler)
- Aktion: `C:\pdf-tools\run_split.bat`
- "Starten in": `C:\pdf-tools`
- "Mit höchsten Privilegien ausführen" (optional)
- Trigger: z. B. täglich 22:00 oder bei Systemstart.

## Hinweise
- Leerseiten-Erkennung ist heuristisch (Text oder Bilder → nicht leer).
- Alle generierten PDFs werden vor dem Speichern von PDF-Tags bereinigt (Katalog: `/StructTreeRoot`, `/MarkInfo`, `/RoleMap`; Seiten: `/Tabs`, `/StructParents`).
- Pfade in `.bat`/`.ps1` bei Bedarf anpassen.
- Für Debugging: Ausgaben in Datei umleiten (z. B. `>> C:\pdf-tools\run.log 2>&1`).

Lizenz: MIT

## SharePoint → Lokaler Share

Mit `copy-sharepoint-to-local.ps1` können Dateien aus einer SharePoint-Online-Dokumentbibliothek auf ein lokales oder UNC-Ziel kopiert werden.

Voraussetzungen:
- PowerShell 5.1 oder neuer
- Modul PnP.PowerShell (einmalig installieren):
  ```powershell
  Install-Module PnP.PowerShell -Scope CurrentUser
  ```

Beispiele:
```powershell
# Interaktive Anmeldung, gesamte Bibliothek kopieren
powershell -File copy-sharepoint-to-local.ps1 `
  -SiteUrl https://tenant.sharepoint.com/sites/Team `
  -LibraryName "Shared Documents" `
  -LocalPath \\fileserver\share\TeamDocs `
  -Recursive -Overwrite

# Nur Unterordner kopieren (server-relative URL), nur neue/aktualisierte Dateien seit Datum
powershell -File copy-sharepoint-to-local.ps1 `
  -SiteUrl https://tenant.sharepoint.com/sites/Team `
  -ServerRelativeUrl "/sites/Team/Shared Documents/Export" `
  -LocalPath C:\exports `
  -ModifiedSince "2025-01-01"
```

## Docker

Zwei Container-Optionen stehen bereit:

- Python-Tool (Split + Clean):
  - Build (Kontext ist der Ordner mit Dockerfile/Script/requirements):
    ```bash
    docker build -t pdf-tools-python -f new-projects/pdf-tools/Dockerfile new-projects/pdf-tools
    ```
  - Run (Volumes für Ein-/Ausgabe/Archiv mounten; nutzt Projektstruktur):
    ```bash
    docker run --rm \
      -v /host/work/01_input:/01_input \
      -v /host/work/02_processed:/02_processed \
      -v /host/work/03_cleaned:/03_cleaned \
      -v /host/work/99_archived:/99_archived \
      pdf-tools-python \
      --in-dir /01_input \
      --out-dir-split /02_processed \
      --out-dir-clean /03_cleaned \
      --archive-dir /99_archived \
      --every 2 \
      --min-alnum-ratio 0.2 \
      --no-image-nonblank \
      --min-bytes 6000 \
      --debug-pages \
      --log-file ./logs/pdf.log

    ```

- SharePoint → Lokaler Share (PnP.PowerShell):
  - Build:
    ```bash
    docker build -t pdf-tools-sharepoint -f new-projects/pdf-tools/Dockerfile.sharepoint new-projects/pdf-tools
    ```
  - Run (Zielordner nach `/data` mounten, Auth per DeviceLogin):
    ```bash
    docker run --rm -it \
      -e SITE_URL="https://tenant.sharepoint.com/sites/Team" \
      -e LIBRARY_NAME="Shared Documents" \
      -e SOURCE_FOLDER="Export" \
      -e AUTH=DeviceLogin \
      -e OVERWRITE=true \
      -v /host/exports:/data \
      pdf-tools-sharepoint
    ```
  - Alternativ mit Server-Relative-URL:
    ```bash
    docker run --rm -it \
      -e SITE_URL="https://tenant.sharepoint.com/sites/Team" \
      -e SERVER_RELATIVE_URL="/sites/Team/Shared Documents/Export" \
      -v /host/exports:/data \
      pdf-tools-sharepoint
    ```
