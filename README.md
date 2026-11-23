# Polimedia

Ein ruhiger, chronologischer Feed für Politik und Geopolitik aus einer festen Quellenliste. Keine Likes, kein Algorithmus, keine Shorts.

## So funktioniert's

```
sources.csv  →  scripts/fetch_feeds.py  →  site/feed.json  →  site/index.html
(Quellen)       (holt alle 30 Min. ab)     (alle Beiträge)     (die Seite)
```

Die Automatik in `.github/workflows/feed.yml` startet das Skript alle 30 Minuten auf GitHub und veröffentlicht danach die Seite neu. Es gibt keinen eigenen Server und keine Datenbank.

## Ordner

| Datei | Was sie macht |
| --- | --- |
| `sources.csv` | Die Quellenliste. Hier Quellen hinzufügen oder löschen. |
| `scripts/fetch_feeds.py` | Holt die Feeds ab und schreibt `site/feed.json`. |
| `site/index.html` | Die Webseite. Liest nur `feed.json`. |
| `.github/workflows/feed.yml` | Die Automatik (GitHub Actions). |
| `requirements.txt` | Das eine Python-Paket, das gebraucht wird (feedparser). |

## Einrichten (einmalig)

1. Auf github.com ein neues Repository anlegen, z.B. `polimedia`, Sichtbarkeit **Public** (GitHub Pages ist im kostenlosen Plan nur für öffentliche Repos verfügbar).
2. Alle Dateien aus diesem Ordner hochladen („Add file“ → „Upload files“), inklusive des versteckten Ordners `.github`.
3. Unter **Settings → Pages** bei „Source“ **GitHub Actions** auswählen.
4. Unter **Actions** den Workflow „Feed aktualisieren“ öffnen und **Run workflow** klicken.
5. Nach 1–2 Minuten steht die Adresse der Seite unter **Settings → Pages**.

## Als App aufs Handy

Polimedia ist eine installierbare Web-App (PWA): eigenes Icon, startet ohne Adressleiste, zeigt offline den zuletzt geladenen Feed.

- **Android (Chrome):** Seite öffnen → Menü (⋮) → „App installieren“ bzw. „Zum Startbildschirm hinzufügen“.
- **iPhone (Safari):** Seite öffnen → Teilen-Symbol → „Zum Home-Bildschirm“.

Updates kommen automatisch, neu installieren ist nie nötig.

## Quelle hinzufügen

Eine Zeile in `sources.csv` ergänzen und speichern. Die Automatik läuft danach von selbst neu.

- Nachrichtenseite: `typ` = `rss`, `feed_url` = Adresse des RSS-Feeds
- YouTube-Kanal: `typ` = `youtube`, `feed_url` = `https://www.youtube.com/feeds/videos.xml?playlist_id=UULF…` (Channel-ID ohne die ersten zwei Buchstaben `UC`, davor `UULF`: so kommen nur lange Videos, keine Shorts)

## Lokal testen

```
pip install -r requirements.txt
python scripts/fetch_feeds.py
cd site && python -m http.server 8000
```

Dann im Browser `http://localhost:8000` öffnen.

## Gut zu wissen

- Die Seite hat `noindex`, taucht also nicht bei Google auf. Wer den Link hat, kommt aber drauf.
- YouTube-Videos laden erst beim Antippen (über youtube-nocookie.com). Die Vorschaubilder kommen allerdings direkt von YouTube.
- GitHub pausiert zeitgesteuerte Automatiken, wenn 60 Tage lang nichts am Repository geändert wurde. Dann einmal „Run workflow“ klicken.
- Gemerkte Beiträge liegen nur im eigenen Browser.
