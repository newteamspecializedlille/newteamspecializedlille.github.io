import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import parse_results  # noqa: E402
import pdf_results  # noqa: E402

ROW = """<tr><td class="tdCal {c}">{d}</td><td class="tdCal {c}">{n}</td><td class="tdCal {c}">ORGA</td>
<td class="tdCal {c}"><!--<form><button>Resultats</button></form>-->
<a href="Route/2026/{n}/Classements.pdf">Resultats</a></td></tr>"""
HTML = "<table>" + "".join([
    ROW.format(c="Course", d="07/03/2026", n="HASPRES"),
    ROW.format(c="Departemental Nord", d="10/05/2026", n="MARQUETTE EN OSTREVENT"),
    ROW.format(c="Departemental Pas de Calais", d="10/05/2026", n="LOOS EN GOHELLE"),
    ROW.format(c="Regional", d="14/06/2026", n="HASPRES2"),
    '<tr><td class="tdCal National1">11/07/2026</td><td class="tdCal National2">FOUSSIGNAC</td>'
    '<td class="tdCal National2">CSD59</td><td class="tdCal National3">'
    '<a href="Route/2026/FOUSSIGNAC/Classements.pdf">Resultats</a></td></tr>',
    '<tr><td class="tdCal Course">01/12/2026</td><td class="tdCal Course">FUTURE</td>'
    '<td class="tdCal Course">X</td><td class="tdCal Course"></td></tr>',
]) + "</table>"


class CalendarTest(unittest.TestCase):
    def test_calendar_rows(self):
        rows = parse_results.parse_calendar(HTML)
        got = {r["date"]: (r["pdf"], r["championship"]) for r in rows}
        self.assertEqual(got["2026/03/07"], ("Route/2026/HASPRES/Classements.pdf", None))
        self.assertEqual(got["2026/06/14"][1], "Championnat Département")
        self.assertEqual(got["2026/07/11"][1], "Championnat National")
        self.assertEqual([r["championship"] for r in rows if r["date"] == "2026/05/10"],
                         ["Championnat Nord", "Championnat Pas-de-Calais"])
        self.assertIsNone(got["2026/12/01"][0])  # pas encore de résultats

    def test_vtt_age_categories(self):
        names = [pdf_results.canonical_sheet_name(t) for t in
                 ("VTT 20/29 ans", "VTT 30/39 ans", "VTT 40/49 ans", "VTT 50/59 ans", "VTT 60 et +")]
        self.assertEqual(names, ["Seniors A", "Seniors B", "Vétérans A", "Vétérans B", "Vétérans C"])
        self.assertEqual(pdf_results.canonical_sheet_name("Masculins 30/39 ans"), "Masculins 30/39 ans")


if __name__ == "__main__":
    unittest.main()
