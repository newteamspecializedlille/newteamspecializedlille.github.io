import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pdf_results  # noqa: E402
import site_links  # noqa: E402
import team_members  # noqa: E402

TEAM = "TEAM SPECIALIZED LILLE"


def sheet(rows):
    return pdf_results.PdfSheet("1ère", ["Place", "Nom", "Club", "Tours", "Temps", "Ecart"], rows)


class PointsTest(unittest.TestCase):
    def test_points(self):
        pts = team_members.ChallengePoints(10, 3, 2, 1, 10)
        self.assertEqual([pts.points_for_place(p) for p in (1, 2, 5, 6, 10, 11, 15, 16)],
                         [20, 13, 13, 12, 12, 11, 11, 10])
        self.assertEqual(pts.points_for_place("AB"), 0)
        self.assertEqual(pts.points_for_results({"a": 1, "b": "AB", "c": 20}), 30)
        self.assertEqual(pts.points_for_results(None), 0)

    def test_challenge_functions_use_same_scale(self):
        pts = team_members.ChallengePoints(10, 3, 2, 1, 10)
        m = team_members.TeamMember("X Y")
        m.road = {"2026": {"a": 1}}
        m.cx = {"2027": {"a": 2}}
        m.vtt = {"2027": {"b": 6}}
        self.assertEqual(m.challenge_calcul_point("2026", pts), 20)
        self.assertEqual(m.challenge_calcul_point_boue("2027", pts), 13 + 12)


class MatchingTest(unittest.TestCase):
    ROSTER = ["FONTAINE HECTOR", "DUFOUR JULIEN"]

    def test_accents_case_order_ignored(self):
        rows = [["3", "Fontaine Héctor", "?", "5", "0:50:00", ""], ["4", "JULIEN DUFOUR", "Transpondeur", "", "", ""]]
        s = pdf_results.PdfSheet("1ère", [], [])
        s._rows += rows
        keys = {pdf_results.name_key(n) for n in self.ROSTER}
        self.assertTrue(all(pdf_results.name_key(r[1]) in keys for r in rows))

    def test_suspect_name_alert(self):
        s = sheet([["3", "FONTAINE HECTEUR", "AUTRE CLUB", "5", "0:50:00", ""],
                   ["4", "DUFOUR MAEL", "AUTRE CLUB", "5", "0:50:00", ""],
                   ["5", "FONTAINE Héctor", TEAM, "5", "0:50:00", ""]])
        found = pdf_results.suspect_names([s], self.ROSTER)
        self.assertEqual([(f[1], f[3]) for f in found], [("FONTAINE HECTEUR", "FONTAINE HECTOR")])


class LinksTest(unittest.TestCase):
    def test_slug_like_jekyll(self):
        self.assertEqual(site_links.jekyll_slug("MAULDE---CHORETTE"), "MAULDE-CHORETTE")
        self.assertEqual(site_links.jekyll_slug("BRUILLE-SAINT-AMAND-"), "BRUILLE-SAINT-AMAND")
        self.assertEqual(site_links.jekyll_slug("MAULDE-(CHORETTE)"), "MAULDE-(CHORETTE)")

    def test_unique_post_on_date_fallback(self):
        posts = {("road", "2024/05/26"): [("2024Departement", "/vtt/2024/03/24/Route2024Departement")]}
        member = {"road": {"2024": {"2024/05/26|Departemental|Equipe": 2}}}
        urls = site_links.build_race_urls([member], posts)
        self.assertEqual(urls["road|2024/05/26|Departemental"], "/vtt/2024/03/24/Route2024Departement")


if __name__ == "__main__":
    unittest.main()
