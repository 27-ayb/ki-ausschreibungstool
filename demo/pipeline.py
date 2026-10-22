#!/usr/bin/env python3
"""
KI-Demo: von der italienischen Ausschreibung zum geprüften Referenzvorschlag.

  Schritt 1  KI liest die Ausschreibung (Italienisch) → strukturiertes Anforderungsprofil (Deutsch)
  Schritt 2  Code prüft jedes Zitat gegen das Original                      (Grounding-Check)
  Schritt 3  Code filtert und rankt die Referenzen                          (matching/matching.py)
  Schritt 4  KI schreibt den Referenztext auf Deutsch und Italienisch
  Schritt 5  Code prüft jede Zahl im Text gegen die Datenbank               (Faktencheck)
  Ergebnis   Vorschlag zur Freigabe – entscheiden muss ein Mensch.

Aufruf:
  uv run demo/pipeline.py                  # live mit ANTHROPIC_API_KEY, sonst offline
  uv run demo/pipeline.py --offline        # immer mit Beispielantworten
  uv run demo/pipeline.py --halluzination  # simuliert einen KI-Fehler: der Faktencheck muss ihn finden
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent
sys.path.insert(0, str(ROOT / "matching"))

import matching as mt  # noqa: E402
from ki import KI, Antwort, LiveKI, OfflineKI  # noqa: E402
from modelle import Anforderungsprofil, Referenztext  # noqa: E402
from pruefungen import Belegpruefung, Zahlpruefung, faktencheck, grounding_check  # noqa: E402

BLAU, GRUEN, GELB, ROT, GRAU = "#5AA9E6", "#43A85A", "#E8A33A", "#E0533F", "#8A96A3"
EINGABE = HIER / "ausschreibung_fiktiv_tal.txt"


@dataclass
class Ergebnis:
    profil: Antwort[Anforderungsprofil]
    belege: list[Belegpruefung]
    vorschlaege: list[mt.Ergebnis]
    ausgefiltert: list[mt.Ergebnis]
    ampel: str
    text: Antwort[Referenztext] | None
    zahlen: list[Zahlpruefung]

    @property
    def probleme(self) -> list[str]:
        p = [f"Beleg „{b.anforderung}“: {b.status}" for b in self.belege if b.status != "belegt"]
        if not self.vorschlaege:
            p.append("Referenzlücke: kein Projekt erfüllt alle Anforderungen")
        p += [f"Zahl „{z.fundstelle}“ ({z.sprache}) nicht in der Datenbank" for z in self.zahlen if not z.ok]
        return p


def ausfuehren(ki: KI, original: str, projekte: list[dict], halluzination: bool = False) -> Ergebnis:
    profil = ki.anforderungen_extrahieren(original)
    belege = grounding_check(profil.daten, original)
    vorschlaege, ausgefiltert, ampel = mt.matche(projekte, profil.daten.fuer_matching())

    text, zahlen = None, []
    if vorschlaege:
        bestes = vorschlaege[0].projekt
        text = ki.referenztext_schreiben(bestes, profil.daten)
        if halluzination:  # simuliert einen typischen Modellfehler: eine falsche Zahl
            text.daten.text_de = text.daten.text_de.replace("120.000", "150.000")
        zahlen = faktencheck(text.daten, bestes)
    return Ergebnis(profil, belege, vorschlaege, ausgefiltert, ampel, text, zahlen)


# ---------------------------------------------------------------- Darstellung

def _schritt(nr: int, titel: str, art: str) -> Text:
    farbe = BLAU if art == "KI" else GRAU
    return Text.assemble((f" {nr} ", f"bold white on {farbe}"), "  ", (titel, "bold"), "   ", (art, farbe))


def _status(ok: bool, ja: str, nein: str) -> Text:
    return Text(f"● {ja}", GRUEN) if ok else Text(f"● {nein}", ROT)


def _euro(wert: float) -> str:
    return f"{wert:,.0f} €".replace(",", ".")


def anzeigen(c: Console, e: Ergebnis, modus: str, halluzination: bool) -> None:
    p = e.profil.daten
    kopf = Table.grid(padding=(0, 2))
    kopf.add_row(Text("Eingabe", GRAU), f"{EINGABE.name}  (Italienisch)")
    kopf.add_row(Text("KI", GRAU), modus)
    if halluzination:
        kopf.add_row(Text("Test", GRAU), Text("Halluzination simuliert: eine falsche Zahl im deutschen Text", GELB))
    c.print(Panel(kopf, title="[bold]KI-Ausschreibungsassistent[/]  ·  Demo", title_align="left",
                  border_style=BLAU, padding=(1, 2)))

    # Schritt 1 + 2
    c.print(_schritt(1, "Anforderungsanalyse", "KI"), "  +  ", _schritt(2, "Grounding-Check", "Code"))
    c.print(Text.assemble(("  Gegenstand  ", GRAU), p.auftragsgegenstand))
    frist = ".".join(reversed(p.abgabefrist.split("-"))) if p.abgabefrist else "–"
    volumen = _euro(p.geschaetztes_volumen_eur) if p.geschaetztes_volumen_eur else "–"
    c.print(Text.assemble(("  Abgabe      ", GRAU), frist, ("     Volumen  ", GRAU), volumen))
    status = {b.anforderung: b for b in e.belege}
    t = Table(box=box.SIMPLE_HEAD, header_style=GRAU, padding=(0, 1), expand=True)
    t.add_column("Anforderung", ratio=3)
    t.add_column("Art", ratio=2)
    t.add_column("Beleg im Original", ratio=3)
    zeilen = [(f"SOA {s.kategorie}, Klasse {s.klassifikation or '–'}", "Ausschluss", f"SOA {s.kategorie}") for s in p.soa]
    r = p.referenzen
    zeilen.append((f"{r.anzahl} Referenz {r.kategorie}, {r.zeitraum_jahre} J., ≥ {_euro(r.mindestwert_eur)}",
                   "Ausschluss", "Referenzen"))
    zeilen += [(z.name, "Ausschluss" if z.pflicht else f"{z.punkte} Punkte", z.name) for z in p.zertifikate]
    zeilen += [(k.kriterium, f"{k.punkte} Punkte", k.kriterium) for k in p.zuschlagskriterien]
    for name, art, schluessel in zeilen:
        b = status[schluessel]
        t.add_row(name, Text(art, ROT if art == "Ausschluss" else BLAU),
                  _status(b.status == "belegt", f"S. {b.seite}, Zitat gefunden", f"S. {b.seite}, {b.status}"))
    c.print(t)
    for frage in p.offene_fragen:
        c.print(Panel(frage, title="Offene Frage für den Vertrieb", title_align="left", border_style=GELB))

    # Schritt 3
    c.print(_schritt(3, "Referenz-Matching", "Code"))
    t = Table(box=box.SIMPLE_HEAD, header_style=GRAU, padding=(0, 1), expand=True)
    t.add_column("Projekt", ratio=3)
    t.add_column("Ergebnis", ratio=2)
    t.add_column("Begründung", ratio=5)
    for rang, v in enumerate(e.vorschlaege, 1):
        score = f"{v.score:.2f}".replace(".", ",")
        t.add_row(v.projekt["name"]["de"], Text(f"Rang {rang}, Score {score}", GRUEN), "; ".join(v.gruende[:3]))
    for a in e.ausgefiltert:
        t.add_row(Text(a.projekt["name"]["de"], GRAU), Text("ausgefiltert", GRAU), Text("; ".join(a.ausschluss), GRAU))
    c.print(t)

    # Schritt 4 + 5
    if e.text:
        c.print(_schritt(4, "Referenztext DE / IT", "KI"), "  +  ", _schritt(5, "Faktencheck", "Code"))
        falsch = {z.fundstelle for z in e.zahlen if not z.ok}

        def markiert(inhalt: str) -> Text:
            text = Text(inhalt)
            for f in falsch:
                text.highlight_words([f], style=f"bold white on {ROT}")
            return text

        c.print(Panel(markiert(e.text.daten.text_de), title="Deutsch", title_align="left", border_style=GRAU))
        c.print(Panel(markiert(e.text.daten.text_it), title="Italiano", title_align="left", border_style=GRAU))
        gesamt, ok = len(e.zahlen), sum(z.ok for z in e.zahlen)
        fehler = gesamt - ok
        verb = "steht" if fehler == 1 else "stehen"
        c.print(Text.assemble("  ", _status(fehler == 0, f"{ok} von {gesamt} Zahlen stimmen mit der Datenbank überein",
                                            f"{fehler} von {gesamt} Zahlen {verb} nicht in der Datenbank")))
        c.print()

    # Ergebnis
    if e.probleme:
        inhalt = Group(Text("Nicht freigabefähig", f"bold {ROT}"),
                       *[Text(f"• {x}") for x in e.probleme],
                       Text("\nDer betroffene Inhalt wird nicht ins Dokument übernommen.", GRAU))
        c.print(Panel(inhalt, border_style=ROT, padding=(1, 2)))
    else:
        inhalt = Group(Text("Bereit zur Freigabe durch den Vertrieb", f"bold {GRUEN}"),
                       Text("Alle Zitate belegt, alle Zahlen geprüft. Die KI schlägt vor, der Mensch entscheidet.", GRAU))
        c.print(Panel(inhalt, border_style=GRUEN, padding=(1, 2)))

    if e.profil.tokens_ein is not None:
        tokens = [e.profil] + ([e.text] if e.text else [])
        ein, aus = sum(a.tokens_ein for a in tokens), sum(a.tokens_aus for a in tokens)
        c.print(Text(f"  Verbrauch: {ein:,} Eingabe- und {aus:,} Ausgabe-Tokens".replace(",", "."), GRAU))


def main() -> int:
    ap = argparse.ArgumentParser(description="KI-Demo: Ausschreibung analysieren, Referenzen finden, Fakten prüfen")
    modus = ap.add_mutually_exclusive_group()
    modus.add_argument("--live", action="store_true", help="Sprachmodell über die Claude API aufrufen")
    modus.add_argument("--offline", action="store_true", help="vorbereitete Beispielantworten verwenden")
    ap.add_argument("--modell", help="Modell-ID für den Live-Modus (Standard: KI_MODELL oder claude-sonnet-5-5)")
    ap.add_argument("--halluzination", action="store_true", help="falsche Zahl einschleusen, um den Faktencheck zu zeigen")
    ap.add_argument("--svg", type=Path, help="Ausgabe zusätzlich als SVG speichern")
    args = ap.parse_args()

    c = Console(record=bool(args.svg), width=100 if args.svg else None)
    live = args.live or (not args.offline and bool(os.environ.get("ANTHROPIC_API_KEY")))
    if args.live and not os.environ.get("ANTHROPIC_API_KEY"):
        c.print(Text("Für --live fehlt der API-Schlüssel. Setzen Sie ANTHROPIC_API_KEY oder starten Sie mit --offline.", ROT))
        return 1

    ki: KI = LiveKI(args.modell) if live else OfflineKI()
    modus = f"live, {ki.modell}" if live else "offline, vorbereitete Beispielantworten (alle Prüfungen laufen echt)"
    original = EINGABE.read_text(encoding="utf-8")
    projekte = json.loads((ROOT / "data" / "referenzprojekte.json").read_text(encoding="utf-8"))

    with c.status("KI arbeitet …", spinner="dots") if live else _ohne_status():
        ergebnis = ausfuehren(ki, original, projekte, args.halluzination)
    anzeigen(c, ergebnis, modus, args.halluzination)

    if args.svg:
        c.save_svg(str(args.svg), title="KI-Ausschreibungsassistent · Demo")
    return 1 if ergebnis.probleme else 0


class _ohne_status:
    def __enter__(self): return self
    def __exit__(self, *_): return False


if __name__ == "__main__":
    raise SystemExit(main())
