"""
Referenz-Matching: findet die passendsten Referenzprojekte für eine Ausschreibung.

Die Logik hat drei Stufen (siehe README, Abschnitt „Matching-Logik“):

  1. Hard Filter  – feste Regeln. Was hier herausfällt, wird nie vorgeschlagen.
  2. Ranking      – gewichteter Score für alle Projekte, die den Filter bestehen.
  3. Auswahl      – trifft immer ein Mensch (im Prototyp: Checkbox „Für dieses Angebot verwenden“).

Nur Python-Standardbibliothek, keine API-Schlüssel nötig.
Ausführen:  python matching/matching.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Gewichte des Scores (Startwerte; im Pilotbetrieb mit echten Ergebnissen zu kalibrieren)
GEWICHTE = {"inhalt": 0.50, "groesse": 0.25, "aktualitaet": 0.15, "auftraggeber": 0.10}


@dataclass
class Ergebnis:
    projekt: dict
    gruende: list[str] = field(default_factory=list)   # warum passend
    ausschluss: list[str] = field(default_factory=list)  # warum ausgefiltert
    score: float | None = None

    @property
    def vorschlag(self) -> bool:
        return not self.ausschluss


# ---------------------------------------------------------------- Hilfsfunktionen

def frühestes_projektende(abgabefrist: date, jahre: int) -> date:
    """Stichtag minus Referenzzeitraum, z. B. 27.11.2026 minus 10 Jahre = 27.11.2016."""
    try:
        return abgabefrist.replace(year=abgabefrist.year - jahre)
    except ValueError:  # 29. Februar
        return abgabefrist.replace(year=abgabefrist.year - jahre, day=28)


def woerter(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüß]+", text.lower()) if len(w) > 3}


def inhaltliche_aehnlichkeit(text_a: str, text_b: str) -> float:
    """
    Platzhalter für die KI-Komponente.

    In der Anwendung vergleicht hier ein Embedding-Modell die Bedeutung zweier Texte
    (z. B. „Schulzentrum“ ≈ „Grundschule“). Für diese Demo genügt eine einfache,
    nachvollziehbare Wortüberschneidung (Jaccard-Index, 0 bis 1).
    """
    a, b = woerter(text_a), woerter(text_b)
    return len(a & b) / len(a | b) if a and b else 0.0


# ---------------------------------------------------------------- Kernlogik

def bewerte(projekt: dict, profil: dict) -> Ergebnis:
    ref = profil["referenzen"]
    frist = date.fromisoformat(profil["abgabefrist"])
    grenze = frühestes_projektende(frist, ref["zeitraum_jahre"])
    ende = date.fromisoformat(projekt["ende"])
    wert = projekt["auftragswert_eur"]
    e = Ergebnis(projekt)

    # Stufe 1 – Hard Filter
    regeln = [
        (projekt["kategorie"] == ref["kategorie"],
         f"Kategorie {projekt['kategorie']} passt", f"Kategorie {projekt['kategorie']} passt nicht"),
        (ende >= grenze,
         f"Abschluss {ende:%m/%Y} im Zeitraum", f"Abschluss {ende:%m/%Y} vor dem {grenze:%d.%m.%Y}"),
        (wert >= ref["mindestwert_eur"],
         f"Auftragswert {wert:,} € ≥ Mindestwert".replace(",", "."),
         f"Auftragswert {wert:,} € unter Mindestwert".replace(",", ".")),
        (not ref.get("nur_oeffentliche_auftraggeber") or projekt["auftraggebertyp"] == "öffentlich",
         "Auftraggebertyp zulässig", "nur öffentliche Auftraggeber zulässig"),
        (projekt["status"] == "geprüft" and projekt["kundenfreigabe"],
         "geprüft und zur Nennung freigegeben", "nicht geprüft oder keine Kundenfreigabe"),
    ]
    for erfuellt, ja, nein in regeln:
        (e.gruende if erfuellt else e.ausschluss).append(ja if erfuellt else nein)

    # Stufe 2 – Ranking (nur für Projekte, die alle Regeln erfüllen)
    if e.vorschlag:
        volumen = profil["geschaetztes_volumen_eur"]
        s_inhalt = inhaltliche_aehnlichkeit(projekt["beschreibung"]["de"], profil["auftragsgegenstand"])
        s_groesse = min(wert, volumen) / max(wert, volumen)
        s_aktualitaet = max(0.0, 1 - (frist - ende).days / (365 * ref["zeitraum_jahre"]))
        s_auftraggeber = 1.0 if projekt["auftraggebertyp"] == "öffentlich" else 0.5
        e.score = round(
            GEWICHTE["inhalt"] * s_inhalt
            + GEWICHTE["groesse"] * s_groesse
            + GEWICHTE["aktualitaet"] * s_aktualitaet
            + GEWICHTE["auftraggeber"] * s_auftraggeber, 2)
    return e


def matche(projekte: list[dict], profil: dict) -> tuple[list[Ergebnis], list[Ergebnis], str]:
    """Gibt (Vorschläge sortiert nach Score, ausgefilterte Projekte, Ampel) zurück."""
    alle = [bewerte(p, profil) for p in projekte]
    vorschlaege = sorted((e for e in alle if e.vorschlag), key=lambda e: e.score, reverse=True)
    ausgefiltert = [e for e in alle if not e.vorschlag]
    ampel = "GRÜN" if len(vorschlaege) >= profil["referenzen"]["anzahl"] else "ROT – Referenzlücke"
    return vorschlaege, ausgefiltert, ampel


# ---------------------------------------------------------------- Demo

def main() -> None:
    projekte = json.loads((DATA / "referenzprojekte.json").read_text(encoding="utf-8"))
    profil = json.loads((DATA / "beispiel_anforderungsprofil.json").read_text(encoding="utf-8"))

    for jahre in (10, 5):
        profil["referenzen"]["zeitraum_jahre"] = jahre
        vorschlaege, ausgefiltert, ampel = matche(projekte, profil)
        print(f"\nReferenzzeitraum {jahre} Jahre  →  Ampel: {ampel}")
        for rang, e in enumerate(vorschlaege, 1):
            print(f"  {rang}. {e.projekt['name']['de']}  (Score {e.score})  – " + "; ".join(e.gruende[:3]))
        for e in ausgefiltert:
            print(f"  ✗  {e.projekt['name']['de']}  – " + "; ".join(e.ausschluss))


if __name__ == "__main__":
    main()
