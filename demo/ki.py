"""
KI-Schicht: ein Interface, zwei Betriebsarten.

  LiveKI     – ruft ein Sprachmodell über die Claude API auf (Structured Outputs).
  OfflineKI  – liefert vorbereitete Beispielantworten im exakt gleichen Format.
               So läuft die Demo überall, ohne API-Schlüssel und ohne Kosten.

Die Prompts werden aus der Prompt-Bibliothek (prompts/*.md) geladen – eine Quelle für
Konzept und Code. Das Ausgabeformat erzwingt das Pydantic-Modell, nicht der Prompt-Text.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Protocol, TypeVar

from modelle import Anforderungsprofil, Referenztext

ROOT = Path(__file__).resolve().parent.parent
BEISPIELE = Path(__file__).resolve().parent / "beispielantworten"
STANDARDMODELL = "claude-sonnet-5-5"

T = TypeVar("T")


@dataclass
class Antwort(Generic[T]):
    daten: T
    quelle: str                 # Modellname oder „Beispielantwort“
    tokens_ein: int | None = None
    tokens_aus: int | None = None


def prompt_laden(datei: str, **werte: str) -> str:
    """Liest den Prompt aus prompts/<datei> (ohne den Abschnitt AUSGABEFORMAT) und setzt Werte ein."""
    markdown = (ROOT / "prompts" / datei).read_text(encoding="utf-8")
    prompt = re.search(r"```text\n(.*?)```", markdown, re.S).group(1)
    prompt = prompt.split("AUSGABEFORMAT")[0].strip()
    for name, wert in werte.items():
        prompt = prompt.replace("{" + name + "}", wert)
    return prompt


ZUSATZREGELN_ANALYSE = """
ZUSATZREGELN FÜR DIE FUNDSTELLE
- Belege jede Anforderung mit der Seitenzahl ([Pagina n]) und einem wörtlichen Zitat.
- Das Zitat muss Zeichen für Zeichen im Original stehen, in der Originalsprache, ohne Kürzung in der Mitte.
- Die Referenzkategorie muss eine der vorgegebenen internen Kategorien sein.
- Alle Beschreibungen und offenen Fragen auf Deutsch."""


class KI(Protocol):
    def anforderungen_extrahieren(self, original: str) -> Antwort[Anforderungsprofil]: ...
    def referenztext_schreiben(self, projekt: dict, profil: Anforderungsprofil) -> Antwort[Referenztext]: ...


class LiveKI:
    def __init__(self, modell: str | None = None) -> None:
        from anthropic import Anthropic  # erst hier importieren: Offline-Modus braucht das Paket nicht

        self.client = Anthropic()  # liest ANTHROPIC_API_KEY aus der Umgebung
        self.modell = modell or os.environ.get("KI_MODELL", STANDARDMODELL)

    def _parse(self, prompt: str, modell_klasse: type[T]) -> Antwort[T]:
        antwort = self.client.messages.parse(
            model=self.modell,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            output_format=modell_klasse,
        )
        return Antwort(antwort.parsed_output, self.modell, antwort.usage.input_tokens, antwort.usage.output_tokens)

    def anforderungen_extrahieren(self, original: str) -> Antwort[Anforderungsprofil]:
        prompt = prompt_laden("01_anforderungsanalyse.md", ausschreibungsunterlagen=original)
        return self._parse(prompt + "\n" + ZUSATZREGELN_ANALYSE, Anforderungsprofil)

    def referenztext_schreiben(self, projekt: dict, profil: Anforderungsprofil) -> Antwort[Referenztext]:
        prompt = prompt_laden(
            "03_referenztext.md",
            referenzdaten=json.dumps(projekt, ensure_ascii=False, indent=2),
            ausschreibungsgegenstand=profil.auftragsgegenstand,
            zuschlagskriterien="; ".join(f"{k.kriterium} ({k.punkte} Punkte)" for k in profil.zuschlagskriterien),
        )
        return self._parse(prompt, Referenztext)


class OfflineKI:
    """Gleiche Schnittstelle, vorbereitete Antworten. Alle Prüfungen danach laufen echt."""

    def anforderungen_extrahieren(self, original: str) -> Antwort[Anforderungsprofil]:
        daten = json.loads((BEISPIELE / "anforderungsprofil.json").read_text(encoding="utf-8"))
        return Antwort(Anforderungsprofil.model_validate(daten), "Beispielantwort")

    def referenztext_schreiben(self, projekt: dict, profil: Anforderungsprofil) -> Antwort[Referenztext]:
        daten = json.loads((BEISPIELE / "referenztext.json").read_text(encoding="utf-8"))
        return Antwort(Referenztext.model_validate(daten), "Beispielantwort")
