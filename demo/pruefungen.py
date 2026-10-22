"""
Guardrails: deterministische Prüfungen NACH jeder KI-Antwort.

Die KI wird nicht blind vertraut. Zwei Prüfungen laufen als normaler Code:

  1. Grounding-Check  – Steht jedes Zitat wirklich so im Original, auf der genannten Seite?
  2. Faktencheck      – Stimmt jede Zahl im generierten Text mit der Datenbank überein?

Beide sind reine Regeln, ohne KI. Was sie nicht bestehen, geht nicht ins Dokument.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from modelle import Anforderungsprofil, Referenztext

# ---------------------------------------------------------------- 1. Grounding-Check

@dataclass
class Belegpruefung:
    anforderung: str
    seite: int
    status: str  # "belegt" | "falsche Seite" | "nicht gefunden"


def _normalisieren(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def seiten_aufteilen(original: str) -> dict[int, str]:
    """Zerlegt den Text an den Markierungen [Pagina n] in Seiten."""
    teile = re.split(r"\[Pagina (\d+)\]", original)
    return {int(teile[i]): _normalisieren(teile[i + 1]) for i in range(1, len(teile) - 1, 2)}


def grounding_check(profil: Anforderungsprofil, original: str) -> list[Belegpruefung]:
    seiten = seiten_aufteilen(original)
    ergebnis = []
    for anforderung, beleg in profil.belege():
        zitat = _normalisieren(beleg.zitat)
        if zitat and zitat in seiten.get(beleg.seite, ""):
            status = "belegt"
        elif zitat and any(zitat in s for s in seiten.values()):
            status = "falsche Seite"
        else:
            status = "nicht gefunden"
        ergebnis.append(Belegpruefung(anforderung, beleg.seite, status))
    return ergebnis


# ---------------------------------------------------------------- 2. Faktencheck

@dataclass
class Zahlpruefung:
    sprache: str
    fundstelle: str  # die Zahl, wie sie im Text steht
    ok: bool


# Ziffernfolgen, die nicht direkt auf einen Buchstaben folgen (so bleibt „OS30“ außen vor)
_ZAHL = re.compile(r"(?<![A-Za-zÀ-ÿ\d])\d[\d.,]*\d|(?<![A-Za-zÀ-ÿ\d])\d")


def _ziffern(fundstelle: str) -> str:
    """'120.000,00' → '120000'; '01/2020' wird vorher in '01' und '2020' getrennt."""
    ohne_cent = re.sub(r",\d{2}$", "", fundstelle.strip())
    return re.sub(r"[.,]", "", ohne_cent).lstrip("0") or "0"


def erlaubte_zahlen(projekt: dict) -> set[str]:
    """Alle Zahlen, die aus dem Datenbank-Datensatz stammen dürfen."""
    erlaubt = {_ziffern(str(int(projekt["auftragswert_eur"])))}
    for feld in ("beginn", "ende"):
        d = date.fromisoformat(projekt[feld])
        erlaubt |= {str(d.year), str(d.month)}
    return erlaubt


def faktencheck(text: Referenztext, projekt: dict) -> list[Zahlpruefung]:
    erlaubt = erlaubte_zahlen(projekt)
    ergebnis = []
    for sprache, inhalt in (("DE", text.text_de), ("IT", text.text_it)):
        for treffer in _ZAHL.finditer(inhalt):
            fundstelle = treffer.group().strip()
            ergebnis.append(Zahlpruefung(sprache, fundstelle, _ziffern(fundstelle) in erlaubt))
    return ergebnis
