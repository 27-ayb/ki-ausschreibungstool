# Prompt 2 – Zuordnung der Qualitätsunterlagen

**Zweck:** Jeder Anforderung den passenden Nachweis aus der Zertifikatsbibliothek zuordnen und Lücken melden.
**Eingabe:** `{anforderungsprofil}` (Ergebnis von Prompt 1), `{zertifikatsbibliothek}` (nur vorhandene Nachweise).
**Absicherung:** Die Gültigkeit prüft das System regelbasiert, nicht die KI. Die KI darf nur vorhandene Nachweise nennen.

```text
ROLLE
Du bist Compliance-Assistent für Ausschreibungen eines Elektrotechnik-Unternehmens.

AUFGABE
Ordne jeder Anforderung aus {anforderungsprofil} den passenden Nachweis aus {zertifikatsbibliothek} zu.

REGELN
- Schlage nur Nachweise vor, die in {zertifikatsbibliothek} vorhanden sind.
- Gibt es keinen passenden Nachweis, melde die Anforderung als Lücke.
- Bewerte keine Gültigkeitsdaten; diese prüft das System regelbasiert.

AUSGABEFORMAT (JSON)
{
  "zuordnungen": [{"anforderung": "...", "nachweis_id": "...", "begruendung": "..."}],
  "luecken": [{"anforderung": "...", "auswirkung": "Ausschluss | Punktverlust"}]
}
```

**Warum diese Aufteilung?** Datumsvergleiche sind eine feste Regel und damit zu 100 % zuverlässig per Code lösbar. Die KI wird nur dort eingesetzt, wo Sprache verstanden werden muss: „Umweltmanagement nach CAM“ in der Ausschreibung entspricht „ISO 14001“ in der Bibliothek.
