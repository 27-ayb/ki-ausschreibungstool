"""
Datenmodelle (Pydantic) für die strukturierten KI-Ausgaben.

Die Modelle sind der „Vertrag“ zwischen KI und Code: Das Sprachmodell muss exakt diese
Struktur liefern (Structured Outputs). Antworten, die nicht passen, werden abgelehnt.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Interne Taxonomie der Referenzdatenbank. Die KI muss die Ausschreibung einer dieser
# Kategorien zuordnen – sie kann keine neue erfinden.
Kategorie = Literal["Energietechnik", "Photovoltaik", "Gebäudetechnik", "Automation", "Service"]

Datenbankfeld = Literal[
    "name", "ort", "auftraggeber", "auftraggebertyp", "beginn", "ende",
    "auftragswert_eur", "kategorie", "soa_kategorie", "beschreibung", "rolle",
]


class Beleg(BaseModel):
    """Fundstelle im Original. Wird nach der KI-Antwort per Code überprüft."""

    seite: int = Field(description="Seitenzahl laut Markierung [Pagina n] im Original")
    zitat: str = Field(description="Wörtliches Zitat aus dem Original, unverändert, höchstens 200 Zeichen")


class SOAAnforderung(BaseModel):
    kategorie: str = Field(description="SOA-Kategorie, z. B. OS30 oder OG11")
    klassifikation: str | None = Field(description="Mindestklasse, z. B. II; null wenn nicht angegeben")
    beleg: Beleg


class Referenzanforderung(BaseModel):
    kategorie: Kategorie = Field(description="Passende interne Kategorie für die geforderten Referenzen")
    zeitraum_jahre: int = Field(description="Referenzzeitraum in Jahren")
    mindestwert_eur: float = Field(description="Mindestauftragswert je Referenz in Euro, netto")
    anzahl: int = Field(description="Geforderte Anzahl von Referenzen")
    nur_oeffentliche_auftraggeber: bool
    beleg: Beleg


class Zertifikat(BaseModel):
    name: str = Field(description="z. B. ISO 14001 oder UNI/PdR 125:2022")
    pflicht: bool = Field(description="true = Ausschlusskriterium, false = Prämienpunkte")
    punkte: int | None = Field(description="Prämienpunkte; null bei Pflichtnachweisen")
    beleg: Beleg


class Zuschlagskriterium(BaseModel):
    kriterium: str
    punkte: int | None
    beleg: Beleg


class Anforderungsprofil(BaseModel):
    auftragsgegenstand: str = Field(description="Kurze Beschreibung auf Deutsch")
    abgabefrist: str | None = Field(description="Datum im Format YYYY-MM-DD; null wenn nicht angegeben")
    geschaetztes_volumen_eur: float | None
    soa: list[SOAAnforderung]
    referenzen: Referenzanforderung
    zertifikate: list[Zertifikat]
    zuschlagskriterien: list[Zuschlagskriterium]
    offene_fragen: list[str] = Field(description="Unklare oder widersprüchliche Stellen, auf Deutsch")

    @field_validator("abgabefrist")
    @classmethod
    def datum_pruefen(cls, wert: str | None) -> str | None:
        if wert is not None:
            date.fromisoformat(wert)  # wirft einen Fehler bei ungültigem Datum
        return wert

    def belege(self) -> list[tuple[str, Beleg]]:
        """Alle Anforderungen mit ihrer Fundstelle, für den Grounding-Check."""
        paare = [(f"SOA {s.kategorie}", s.beleg) for s in self.soa]
        paare.append(("Referenzen", self.referenzen.beleg))
        paare += [(z.name, z.beleg) for z in self.zertifikate]
        paare += [(k.kriterium, k.beleg) for k in self.zuschlagskriterien]
        return paare

    def fuer_matching(self) -> dict:
        """Übersetzt das Profil in das Format der Matching-Logik (matching/matching.py)."""
        return {
            "auftragsgegenstand": self.auftragsgegenstand,
            "abgabefrist": self.abgabefrist,
            "geschaetztes_volumen_eur": self.geschaetztes_volumen_eur,
            "referenzen": self.referenzen.model_dump(exclude={"beleg"}),
        }


class Referenztext(BaseModel):
    text_de: str = Field(description="Referenztext auf Deutsch, höchstens 120 Wörter")
    text_it: str = Field(description="Derselbe Inhalt auf Italienisch, höchstens 120 Wörter")
    verwendete_felder: list[Datenbankfeld] = Field(description="Datenbankfelder, deren Fakten im Text vorkommen")
