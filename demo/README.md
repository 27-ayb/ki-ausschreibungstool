# KI-Demo: vertrauenswürdige KI für Ausschreibungen

Diese Demo zeigt den Kern des Tools als lauffähigen Code: Eine **italienische Ausschreibung** wird von einem Sprachmodell gelesen, in ein **strukturiertes deutsches Anforderungsprofil** übersetzt, mit der Referenzdatenbank abgeglichen und in einen **zweisprachigen Referenztext** überführt.

Der entscheidende Punkt ist nicht, *dass* die KI das kann, sondern dass **jedes KI-Ergebnis anschließend per Code überprüft wird**, bevor es ins Dokument darf.

![Demo mit simulierter Halluzination: der Faktencheck findet die falsche Zahl](../docs/demo_halluzination.svg)

## Ablauf

| Schritt | Wer | Was passiert |
| --- | --- | --- |
| 1. Anforderungsanalyse | KI | Liest die italienische Ausschreibung und liefert ein Anforderungsprofil auf Deutsch, erzwungen durch ein festes Datenmodell (Structured Outputs). Jede Anforderung trägt Seite und wörtliches Zitat. |
| 2. Grounding-Check | Code | Prüft, ob jedes Zitat Zeichen für Zeichen auf der genannten Seite im Original steht. |
| 3. Referenz-Matching | Code | Hard Filter und Score aus [`matching/matching.py`](../matching/matching.py). |
| 4. Referenztext DE / IT | KI | Schreibt den Text nur aus den Fakten des Datenbank-Datensatzes. |
| 5. Faktencheck | Code | Vergleicht jede Zahl im Text mit der Datenbank. Eine falsche Zahl sperrt die Freigabe. |
| Ergebnis | Mensch | Das System schlägt vor, der Vertrieb entscheidet. |

## Starten

Voraussetzung: [uv](https://docs.astral.sh/uv/) (installiert Python und alle Pakete automatisch).

```bash
uv run demo/pipeline.py --offline          # ohne API-Schlüssel, mit vorbereiteten Beispielantworten
uv run demo/pipeline.py --halluzination    # schleust eine falsche Zahl ein: der Faktencheck muss sie finden
uv run demo/pipeline.py --live             # echter Modellaufruf, braucht ANTHROPIC_API_KEY
uv run pytest                              # 19 automatische Tests
```

**Ohne Installation:** Im Repository auf **Code → Codespaces → Create codespace** klicken. Es öffnet sich eine vollständige Entwicklungsumgebung im Browser, in der die Befehle oben sofort laufen.

## Offline und live

| | Offline | Live |
| --- | --- | --- |
| KI-Antworten | vorbereitete Beispielantworten im exakt gleichen Datenformat | Sprachmodell über die Claude API (`claude-sonnet-5-5`, über `--modell` oder `KI_MODELL` änderbar) |
| Grounding-Check, Matching, Faktencheck | laufen echt | laufen echt |
| Kosten, API-Schlüssel | keine | API-Schlüssel nötig, wenige Cent pro Lauf |

Die Prüfungen unterscheiden nicht zwischen den Modi. Genau das ist das Prinzip: Dem Code ist egal, woher eine Antwort kommt, sie muss die Prüfungen bestehen.

## Dateien

| Datei | Inhalt |
| --- | --- |
| [`pipeline.py`](pipeline.py) | Ablauf und Terminal-Ausgabe |
| [`modelle.py`](modelle.py) | Datenmodelle (Pydantic): der „Vertrag“ zwischen KI und Code |
| [`ki.py`](ki.py) | KI-Schicht mit Live- und Offline-Modus; Prompts kommen aus [`prompts/`](../prompts/) |
| [`pruefungen.py`](pruefungen.py) | Grounding-Check und Faktencheck, reine Regeln ohne KI |
| [`test_demo.py`](test_demo.py) | Tests, u. a. für erfundene Zitate, falsche Seiten und falsche Zahlen |
| [`ausschreibung_fiktiv_tal.txt`](ausschreibung_fiktiv_tal.txt) | Fiktive Ausschreibung auf Italienisch |
| [`beispielantworten/`](beispielantworten/) | Antworten für den Offline-Modus |

## Werkzeuge

Python 3.10+ · [Pydantic](https://docs.pydantic.dev/) für typisierte Datenmodelle · [Claude API Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) · [Rich](https://rich.readthedocs.io/) für die Terminal-Ausgabe · [uv](https://docs.astral.sh/uv/) für Pakete und reproduzierbare Umgebungen (`uv.lock`) · [Ruff](https://docs.astral.sh/ruff/) für Code-Stil · [pytest](https://docs.pytest.org/) · GitHub Actions führt Stilprüfung, Tests und Demo bei jeder Änderung automatisch aus.
