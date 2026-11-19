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
        self.assertEqual(pts.points_for_place(None, "AB"), 0)
        self.assertEqual(pts.points_for_place(3, "AB"), 0)
        results = [team_members.make_result("2026-01-01", "A", "1ère", 1),
                   team_members.make_result("2026-01-02", "B", "1ère", None, "AB"),
                   team_members.make_result("2026-01-03", "C", "1ère", 20)]
        self.assertEqual(pts.points_for_results(results), 30)
        self.assertEqual(pts.points_for_results(None), 0)

    def test_challenge_functions_use_same_scale(self):
        pts = team_members.ChallengePoints(10, 3, 2, 1, 10)
        m = team_members.TeamMember("X Y")
        make = team_members.make_result
        m.road = {"2026": [make("2026-03-01", "a", "1ère", 1)]}
        m.cx = {"2027": [make("2026-11-01", "a", "1ère", 2)]}
        m.vtt = {"2027": [make("2026-11-02", "b", "Seniors B", 6)]}
        self.assertEqual(m.challenge_calcul_point("2026", pts), 20)
        self.assertEqual(m.challenge_calcul_point_boue("2027", pts), 13 + 12)


class ResultsTest(unittest.TestCase):
    def test_upsert_is_idempotent_and_replaces(self):
        m = team_members.TeamMember("X Y")
        make = team_members.make_result
        m.upsert_result("cx", "2027", make("2026-10-18", "LILLERS", "1ère", 9, None, 20))
        m.upsert_result("cx", "2027", make("2026-10-18", "LILLERS", "1ère", 7, None, 21))
        m.upsert_result("cx", "2027", make("2026-10-18", "LILLERS", "2ème", None, "AB", 30))
        self.assertEqual(len(m.cx["2027"]), 2)
        self.assertEqual([r["rank"] for r in m.cx["2027"] if r["category"] == "1ère"], [7])

    def test_remove_race_results_and_sorted_dict(self):
        m = team_members.TeamMember("X Y")
        make = team_members.make_result
        for date, race in (("2026-10-18", "LILLERS"), ("2026-11-01", "HENIN"), ("2026-10-18", "ANZIN")):
            m.upsert_result("cx", "2027", make(date, race, "1ère", 1))
        self.assertEqual(m.remove_race_results("cx", "2027", "2026-10-18", "LILLERS"), 1)
        d = m.to_dict()
        self.assertEqual([(r["date"], r["raceName"]) for r in d["cx"]["2027"]],
                         [("2026-10-18", "ANZIN"), ("2026-11-01", "HENIN")])
        self.assertEqual(set(d), {"name", "cx", "vtt", "road"})

    def test_rank_status(self):
        import parse_results
        self.assertEqual(parse_results.to_rank_status(7), (7, None))
        self.assertEqual(parse_results.to_rank_status("Ab"), (None, "AB"))
        self.assertEqual(parse_results.to_rank_status("AB"), (None, "AB"))


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
        member = {"road": {"2024": [{"date": "2024-05-26", "raceName": "Departemental", "category": "Equipe",
                                     "rank": 2, "status": None, "participants": None}]}}
        urls = site_links.build_race_urls([member], posts)
        self.assertEqual(urls["road|2024/05/26|Departemental"], "/vtt/2024/03/24/Route2024Departement")


if __name__ == "__main__":
    unittest.main()
