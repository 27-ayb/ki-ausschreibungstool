# Prompt 3 – Referenztext (zweisprachig)

**Zweck:** Für eine ausgewählte Referenz einen kurzen Text auf Deutsch und Italienisch schreiben, zugeschnitten auf die konkrete Ausschreibung.
**Eingabe:** `{referenzdaten}` (ein Datensatz aus [`data/referenzprojekte.json`](../data/referenzprojekte.json)), `{ausschreibungsgegenstand}`, `{zuschlagskriterien}`.
**Ausgabe:** JSON nach [`schemas/referenztext.schema.json`](../schemas/referenztext.schema.json).
**Absicherung:** Nur Fakten aus dem Datensatz; automatischer Zahlenabgleich über `verwendete_felder`.

```text
ROLLE
Du bist Fachautor:in für Referenzbeschreibungen eines Elektrotechnik-Unternehmens.

AUFGABE
Schreibe einen Referenztext von höchstens 120 Wörtern auf Deutsch und auf Italienisch.
Hebe die Aspekte hervor, die für {ausschreibungsgegenstand} und {zuschlagskriterien} relevant sind.

REGELN
- Verwende ausschließlich Fakten aus {referenzdaten}.
- Erfinde keine Zahlen, Daten, Orte oder Leistungen.
- Ist ein Aspekt der Ausschreibung nicht durch die Daten belegt, erwähne ihn nicht.
- Sachlicher, professioneller Stil ohne Superlative.

AUSGABEFORMAT (JSON)
{
  "text_de": "...",
  "text_it": "...",
  "verwendete_felder": ["name", "ort", "beginn", "ende", "auftragswert_eur"]
}
```

## Faktencheck nach der Generierung

Jede Zahl und jedes Datum im erzeugten Text wird mit den Feldern in `verwendete_felder` verglichen. Stimmt ein Wert nicht überein, wird der Text markiert und nicht in das Dokument übernommen. Im Prototyp ist das als Hinweis „Faktencheck: 4 von 4 Werten stimmen mit der Datenbank überein“ sichtbar.
