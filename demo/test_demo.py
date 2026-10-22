"""Tests für die KI-Demo: Guardrails, Pipeline und Anbindung an die API (ohne echten Aufruf)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "matching"))

from ki import LiveKI, OfflineKI, prompt_laden  # noqa: E402
from modelle import Anforderungsprofil, Referenztext  # noqa: E402
from pipeline import EINGABE, ausfuehren  # noqa: E402
from pruefungen import faktencheck, grounding_check  # noqa: E402

ORIGINAL = EINGABE.read_text(encoding="utf-8")
PROJEKTE = json.loads((HIER.parent / "data" / "referenzprojekte.json").read_text(encoding="utf-8"))
WALDECK = next(p for p in PROJEKTE if p["id"] == "REF-2020-003")


@pytest.fixture
def profil() -> Anforderungsprofil:
    return OfflineKI().anforderungen_extrahieren(ORIGINAL).daten


@pytest.fixture
def text() -> Referenztext:
    return OfflineKI().referenztext_schreiben(WALDECK, None).daten


# ---------------------------------------------------------------- Grounding-Check

def test_alle_zitate_der_beispielantwort_sind_belegt(profil):
    assert all(b.status == "belegt" for b in grounding_check(profil, ORIGINAL))


def test_erfundenes_zitat_wird_erkannt(profil):
    profil.zertifikate[0].beleg.zitat = "È richiesta la certificazione ISO 50001."
    status = {b.anforderung: b.status for b in grounding_check(profil, ORIGINAL)}
    assert status["ISO 9001"] == "nicht gefunden"


def test_falsche_seitenangabe_wird_erkannt(profil):
    profil.soa[0].beleg.seite = 3
    assert grounding_check(profil, ORIGINAL)[0].status == "falsche Seite"


# ---------------------------------------------------------------- Faktencheck

def test_korrekte_zahlen_bestehen(text):
    pruefungen = faktencheck(text, WALDECK)
    assert pruefungen and all(z.ok for z in pruefungen)


@pytest.mark.parametrize("falsch", ["150.000", "130.000,00", "01/2019"])
def test_falsche_zahl_wird_erkannt(text, falsch):
    text.text_it = text.text_it.replace("120.000" if "000" in falsch else "01/2020", falsch)
    assert any(not z.ok for z in faktencheck(text, WALDECK))


def test_soa_kategorie_ist_keine_zahl(text):
    text.text_de += " Qualifikation SOA OS30."
    assert all(z.ok for z in faktencheck(text, WALDECK))


# ---------------------------------------------------------------- Pipeline

def test_pipeline_offline_schlaegt_waldeck_vor():
    e = ausfuehren(OfflineKI(), ORIGINAL, PROJEKTE)
    assert [v.projekt["id"] for v in e.vorschlaege] == ["REF-2020-003"]
    assert e.probleme == []


def test_pipeline_halluzination_blockiert_freigabe():
    e = ausfuehren(OfflineKI(), ORIGINAL, PROJEKTE, halluzination=True)
    assert any("150.000" in p for p in e.probleme)


def test_pipeline_referenzluecke_ohne_textgenerierung(monkeypatch):
    ki = OfflineKI()
    original = ki.anforderungen_extrahieren

    def fuenf_jahre(text):
        antwort = original(text)
        antwort.daten.referenzen.zeitraum_jahre = 5
        return antwort

    monkeypatch.setattr(ki, "anforderungen_extrahieren", fuenf_jahre)
    e = ausfuehren(ki, ORIGINAL, PROJEKTE)
    assert e.vorschlaege == [] and e.text is None
    assert any("Referenzlücke" in p for p in e.probleme)


# ---------------------------------------------------------------- Prompts und API-Anbindung

def test_prompt_wird_aus_der_bibliothek_geladen():
    prompt = prompt_laden("01_anforderungsanalyse.md", ausschreibungsunterlagen="TEST-TEXT")
    assert "TEST-TEXT" in prompt and "AUSGABEFORMAT" not in prompt


def test_live_ki_nutzt_structured_outputs(monkeypatch, profil):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    ki = LiveKI("claude-sonnet-5-5")
    aufrufe = []

    def parse(**kwargs):
        aufrufe.append(kwargs)
        return SimpleNamespace(parsed_output=profil, usage=SimpleNamespace(input_tokens=1200, output_tokens=800))

    monkeypatch.setattr(ki.client.messages, "parse", parse)
    antwort = ki.anforderungen_extrahieren(ORIGINAL)
    assert aufrufe[0]["output_format"] is Anforderungsprofil
    assert aufrufe[0]["model"] == "claude-sonnet-5-5"
    assert "Pagina 7" in aufrufe[0]["messages"][0]["content"]
    assert antwort.tokens_ein == 1200
