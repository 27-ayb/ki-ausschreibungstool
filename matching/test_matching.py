"""Tests für die Matching-Logik.  Ausführen:  python -m unittest discover matching"""

import json
import unittest
from copy import deepcopy

from matching import DATA, matche

PROJEKTE = json.loads((DATA / "referenzprojekte.json").read_text(encoding="utf-8"))
PROFIL = json.loads((DATA / "beispiel_anforderungsprofil.json").read_text(encoding="utf-8"))


def mit(**referenzen):
    profil = deepcopy(PROFIL)
    profil["referenzen"].update(referenzen)
    return profil


class TestMatching(unittest.TestCase):

    def test_zehn_jahre_schulzentrum_wird_vorgeschlagen(self):
        vorschlaege, ausgefiltert, ampel = matche(PROJEKTE, mit(zeitraum_jahre=10))
        self.assertEqual([e.projekt["id"] for e in vorschlaege], ["REF-2020-003"])
        self.assertEqual(len(ausgefiltert), 3)
        self.assertEqual(ampel, "GRÜN")

    def test_fuenf_jahre_ergibt_referenzluecke(self):
        vorschlaege, _, ampel = matche(PROJEKTE, mit(zeitraum_jahre=5))
        self.assertEqual(vorschlaege, [])
        self.assertTrue(ampel.startswith("ROT"))

    def test_mindestwert_filtert(self):
        vorschlaege, _, _ = matche(PROJEKTE, mit(mindestwert_eur=150000))
        self.assertEqual(vorschlaege, [])

    def test_nur_oeffentliche_auftraggeber(self):
        vorschlaege, _, _ = matche(PROJEKTE, mit(kategorie="Automation", nur_oeffentliche_auftraggeber=True))
        self.assertEqual(vorschlaege, [])

    def test_ohne_kundenfreigabe_kein_vorschlag(self):
        projekte = deepcopy(PROJEKTE)
        for p in projekte:
            p["kundenfreigabe"] = False
        vorschlaege, _, _ = matche(projekte, PROFIL)
        self.assertEqual(vorschlaege, [])

    def test_score_liegt_zwischen_null_und_eins(self):
        vorschlaege, _, _ = matche(PROJEKTE, PROFIL)
        for e in vorschlaege:
            self.assertGreaterEqual(e.score, 0)
            self.assertLessEqual(e.score, 1)


if __name__ == "__main__":
    unittest.main()
