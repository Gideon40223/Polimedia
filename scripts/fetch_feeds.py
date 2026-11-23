"""
Polimedia – Feed-Abholer

Was dieses Skript macht, in vier Schritten:
1. Es liest die Quellenliste (sources.csv).
2. Es holt von jeder Quelle den Feed ab (RSS bei Nachrichtenseiten, YouTube-Feed bei Kanälen).
3. Es zieht aus jedem Beitrag das Wichtige raus: Titel, Anreißer, Link, Bild, Datum.
4. Es schreibt alles, nach Datum sortiert, in eine Datei: site/feed.json.
   Die Webseite liest dann nur noch diese eine Datei.

Starten (im Projektordner):  python scripts/fetch_feeds.py
"""

import csv
import hashlib
import html
import json
import re
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

# --- Einstellungen -----------------------------------------------------------

QUELLEN_DATEI = Path("sources.csv")
AUSGABE_DATEI = Path("site/feed.json")
MAX_ALTER_TAGE = 7          # ältere Beiträge fliegen raus
MAX_PRO_QUELLE = 40         # damit eine sehr aktive Quelle nicht alles zuschüttet
ANREISSER_LAENGE = 280      # Zeichen, danach wird mit "…" gekürzt
USER_AGENT = "Polimedia/1.0 (privater Feed-Reader)"

socket.setdefaulttimeout(20)  # eine Quelle, die nicht antwortet, hält nicht alles auf


# --- Kleine Hilfsfunktionen --------------------------------------------------

def text_saeubern(roh: str) -> str:
    """Entfernt HTML-Schnipsel und doppelte Leerzeichen aus einem Text."""
    ohne_tags = re.sub(r"<[^>]+>", " ", roh or "")
    return re.sub(r"\s+", " ", html.unescape(ohne_tags)).strip()


def kuerzen(text: str, laenge: int) -> str:
    """Kürzt einen Text an einer Wortgrenze und hängt '…' an."""
    if len(text) <= laenge:
        return text
    return text[:laenge].rsplit(" ", 1)[0].rstrip(",.;:–- ") + " …"


def datum_von(eintrag) -> datetime | None:
    """Holt das Veröffentlichungsdatum eines Beitrags (in UTC)."""
    zeit = eintrag.get("published_parsed") or eintrag.get("updated_parsed")
    if not zeit:
        return None
    return datetime(*zeit[:6], tzinfo=timezone.utc)


def bild_von(eintrag) -> str | None:
    """Sucht ein Vorschaubild. Feeds verstecken das an verschiedenen Stellen."""
    for feld in ("media_thumbnail", "media_content"):
        for medium in eintrag.get(feld) or []:
            url = medium.get("url")
            if url and (feld == "media_thumbnail" or medium.get("medium") == "image"
                        or re.search(r"\.(jpe?g|png|webp)", url, re.I)):
                return url
    for link in eintrag.get("links") or []:
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
            return link.get("href")
    treffer = re.search(r'<img[^>]+src="([^"]+)"', eintrag.get("summary", "") or "")
    return treffer.group(1) if treffer else None


def ist_bezahlartikel(eintrag, quelle: dict) -> bool:
    """
    Erkennt Paywall-Artikel (z.B. FAZ+).
    Noch offen: Wie die FAZ das im Feed markiert, sehen wir erst an echten Daten.
    Sobald wir das wissen, kommt hier die Regel rein.
    """
    return False


def eintrag_umwandeln(eintrag, quelle: dict) -> dict | None:
    """Macht aus einem Feed-Eintrag einen sauberen Beitrag für die Webseite."""
    link = eintrag.get("link")
    titel = text_saeubern(eintrag.get("title", ""))
    datum = datum_von(eintrag)
    if not link or not titel or not datum:
        return None

    ist_video = quelle["typ"] == "youtube"
    video_id = eintrag.get("yt_videoid") if ist_video else None
    if ist_video and not video_id:
        return None

    roh_text = eintrag.get("summary", "") or ""
    if ist_video:
        # YouTube-Beschreibungen sind oft lang und voller Links: nur der erste Absatz.
        roh_text = roh_text.split("\n\n")[0]
        roh_text = re.sub(r"https?://\S+", "", roh_text)
    anreisser = kuerzen(text_saeubern(roh_text), 200 if ist_video else ANREISSER_LAENGE)

    return {
        "id": hashlib.sha1(link.encode()).hexdigest()[:12],
        "quelle": quelle["name"],
        "kategorie": quelle["kategorie"],
        "typ": "video" if ist_video else "artikel",
        "titel": titel,
        "anreisser": anreisser,
        "link": link,
        "bild": bild_von(eintrag),
        "video_id": video_id,
        "bezahl": ist_bezahlartikel(eintrag, quelle),
        "datum": datum.isoformat(),
    }


# --- Hauptprogramm -----------------------------------------------------------

def quellen_lesen() -> list[dict]:
    with QUELLEN_DATEI.open(encoding="utf-8") as f:
        return [zeile for zeile in csv.DictReader(f) if zeile.get("feed_url")]


def feed_holen(quelle: dict):
    """Holt einen Feed aus dem Internet. Eigene Funktion, damit man sie im Test ersetzen kann."""
    return feedparser.parse(quelle["feed_url"], agent=USER_AGENT)


def main() -> int:
    quellen = quellen_lesen()
    grenze = datetime.now(timezone.utc) - timedelta(days=MAX_ALTER_TAGE)
    beitraege, status = [], []

    for quelle in quellen:
        try:
            feed = feed_holen(quelle)
            if not feed.entries:
                raise ValueError(feed.get("bozo_exception") or "Feed ist leer")
            neu = [b for e in feed.entries if (b := eintrag_umwandeln(e, quelle))]
            neu = [b for b in neu if b["datum"] >= grenze.isoformat()]
            neu.sort(key=lambda b: b["datum"], reverse=True)
            neu = neu[:MAX_PRO_QUELLE]
            beitraege += neu
            status.append({"name": quelle["name"], "ok": True, "anzahl": len(neu)})
            print(f"OK      {quelle['name']}: {len(neu)} Beiträge")
        except Exception as fehler:  # eine kaputte Quelle soll nicht alles stoppen
            status.append({"name": quelle["name"], "ok": False, "anzahl": 0})
            print(f"FEHLER  {quelle['name']}: {fehler}", file=sys.stderr)

    # Doppelte Links rauswerfen (passiert, wenn eine Meldung in zwei Rubriken steht)
    gesehen, eindeutig = set(), []
    for b in sorted(beitraege, key=lambda b: b["datum"], reverse=True):
        if b["link"] not in gesehen:
            gesehen.add(b["link"])
            eindeutig.append(b)

    ergebnis = {
        "stand": datetime.now(timezone.utc).isoformat(),
        "quellen": [
            {**s, "kategorie": q["kategorie"], "website": q["website"]}
            for s, q in zip(status, quellen)
        ],
        "beitraege": eindeutig,
    }
    AUSGABE_DATEI.parent.mkdir(parents=True, exist_ok=True)
    AUSGABE_DATEI.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Fertig: {len(eindeutig)} Beiträge in {AUSGABE_DATEI}")

    # Nur wenn ALLE Quellen kaputt sind, gilt der Lauf als fehlgeschlagen.
    return 0 if any(s["ok"] for s in status) else 1


if __name__ == "__main__":
    sys.exit(main())
