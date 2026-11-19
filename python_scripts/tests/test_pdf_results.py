"""Tests de lecture des PDF de classement. Lancer : cd python_scripts && python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pdf_results  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def sheets(name, roster=()):
    return {s.name: s for s in pdf_results.extract_sheets(os.path.join(FIX, name), roster)}


def data(sheet):
    return sheet._rows[2:]


class PdfResultsTest(unittest.TestCase):
    def test_sheet_names(self):
        self.assertEqual(pdf_results.canonical_sheet_name("VTT Séniors A"), "Seniors A")
        self.assertEqual(pdf_results.canonical_sheet_name("VTT Vétérans C"), "Vétérans C")
        self.assertEqual(pdf_results.canonical_sheet_name("CX 15/16 ans"), "Cadets")
        self.assertEqual(pdf_results.canonical_sheet_name("2ème Catégorie"), "2ème")
        self.assertEqual(pdf_results.canonical_sheet_name("CX 1e catégorie"), "1ère")

    def test_raismes_cx(self):
        s = sheets("raismes_cx.pdf")
        self.assertEqual([len(data(s[n])) for n in ("1ère", "2ème", "3ème", "Féminines", "Cadets")], [8, 33, 34, 1, 4])
        dejonghe = [r for r in data(s["3ème"]) if "DEJONGHE" in r[1]][0]
        self.assertEqual((dejonghe[0], dejonghe[2], dejonghe[3]), ("29", "TEAM SPECIALIZED LILLE", "5"))
        self.assertTrue(s["3ème"].scratch_eligible)
        self.assertFalse(s["Minimes"].scratch_eligible)

    def test_apostrophe_in_club_kept(self):
        s = sheets("raismes_cx.pdf")
        self.assertEqual(data(s["Cadets"])[0][2], "VELO CLUB DE L'ESCAUT ANZIN")

    def test_vtt_huguenin_is_seniors_b_abandon(self):
        s = sheets("raismes_vtt.pdf")
        row = [r for r in data(s["Seniors B"]) if "HUGUENIN" in r[1]][0]
        self.assertEqual((row[0], row[3], row[4]), ("AB", "", ""))
        self.assertFalse(any("HUGUENIN" in r[1] for r in data(s["Seniors A"])))

    def test_lillers_empty_club_uses_roster(self):
        s = sheets("lillers_cx.pdf", roster=["DERASSE DAVID", "MOULIN FELIX"])
        derasse = [r for r in data(s["1ère"]) if "DERASSE" in r[1]][0]
        self.assertEqual((derasse[0], derasse[2]), ("7", "TEAM SPECIALIZED LILLE"))
        self.assertTrue(s["1ère"].club_column_empty)
        self.assertEqual(len([r for r in data(s["1ère"]) if r[2]]), 1)

    def test_henin_missing_tours_and_abd(self):
        s = sheets("henin_cx.pdf")
        self.assertEqual(len(data(s["1ère"])), 9)
        self.assertEqual([r[0] for r in data(s["1ère"])][-2:], ["AB", "AB"])
        self.assertEqual(data(s["3ème"])[0][3], "")
        self.assertEqual(len(data(s["Cadets"])), 7)

    def test_dash_cell_ignored(self):
        s = sheets("lillers_cx.pdf")
        fardel = [r for r in data(s["Cadets"]) if "Rose" in r[1]][0]
        self.assertEqual(fardel[2], "")

    def test_find_pdf(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "cx"))
            for f in ("RAISMES.pdf", "TERRIL 89 - HENIN BEAUMONT.pdf"):
                open(os.path.join(root, "cx", f), "w").close()
            self.assertTrue(pdf_results.find_pdf(root, "Cyclo Cross", "RAISMES").endswith("RAISMES.pdf"))
            self.assertTrue(pdf_results.find_pdf(root, "Cyclo Cross", "HENIN BEAUMONT").endswith("BEAUMONT.pdf"))
            self.assertIsNone(pdf_results.find_pdf(root, "Cyclo Cross", "LILLERS"))
            self.assertIsNone(pdf_results.find_pdf(root, "VTT", "RAISMES"))


if __name__ == "__main__":
    unittest.main()
