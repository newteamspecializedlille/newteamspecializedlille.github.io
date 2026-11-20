import os
import sys
import tempfile
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

    def test_abandon_can_count_as_participation(self):
        pts = team_members.ChallengePoints(10, 3, 2, 1, 10, abandon_counts=True)
        self.assertEqual(pts.points_for_place(None, "AB"), 10)

    def test_scales_come_from_rules_file(self):
        rules = {"abandon_counts": False,
                 "challenge": {"2024": {"point_win": 3, "point_top5": 2, "point_top10": 1, "point_top15": 0,
                                        "point_participation": 10},
                               "default": {"point_win": 10, "point_top5": 3, "point_top10": 2, "point_top15": 1,
                                           "point_participation": 10}},
                 "boue": {"default": {"point_win": 3, "point_top5": 2, "point_top10": 1, "point_top15": 0,
                                      "point_participation": 10}}}
        old = team_members.ChallengePoints.from_rules("challenge", 2024, rules)
        new = team_members.ChallengePoints.from_rules("challenge", "2026", rules)
        self.assertEqual((old.point_win, new.point_win), (3, 10))
        self.assertEqual(team_members.ChallengePoints.from_rules("boue", 2027, rules).point_win, 3)

    def test_real_rules_file_is_valid(self):
        import json
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_data", "challenge_rules.json")
        rules = json.load(open(path, encoding="utf8"))
        for kind in ("challenge", "boue"):
            self.assertIn("default", rules[kind])
            self.assertEqual(team_members.ChallengePoints.from_rules(kind, 2099, rules).point_participation, 10)


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
        self.assertEqual(set(d), {"name", "active", "cx", "vtt", "road"})

    def test_rank_status(self):
        import parse_results
        self.assertEqual(parse_results.to_rank_status(7), (7, None))
        self.assertEqual(parse_results.to_rank_status("Ab"), (None, "AB"))
        self.assertEqual(parse_results.to_rank_status("AB"), (None, "AB"))


class ActiveMembersTest(unittest.TestCase):
    def test_active_flag_round_trip(self):
        former = team_members.TeamMember("BOONE NICOLAS", active=False)
        current = team_members.TeamMember("DUFOUR JULIEN")
        self.assertFalse(former.to_dict()["active"])
        self.assertTrue(current.to_dict()["active"])
        current.upsert_result("road", "2026", team_members.make_result("2026-03-07", "HASPRES", "2ème", 8))
        former.upsert_result("road", "2026", team_members.make_result("2026-03-07", "HASPRES", "2ème", 1))
        self.assertEqual(current.to_dict()["road"]["2026"][0]["rank"], 8)


class RaceTypeTest(unittest.TestCase):
    def test_race_type_only_when_present(self):
        self.assertNotIn("raceType", team_members.make_result("2026-05-10", "A", "1ère", 1))
        self.assertEqual(team_members.make_result("2026-05-10", "A", "1ère", 1, None, 20, "Championnat Nord")["raceType"],
                         "Championnat Nord")

    def test_set_race_type_on_existing_results(self):
        m = team_members.TeamMember("A")
        m.upsert_result("road", "2026", team_members.make_result("2026-05-10", "MARQUETTE", "2ème", 3))
        m.upsert_result("road", "2026", team_members.make_result("2026-05-17", "AUTRE", "2ème", 1))
        self.assertEqual(m.set_race_type("road", "2026-05-10", "MARQUETTE", "Championnat Nord"), 1)
        self.assertEqual(m.set_race_type("road", "2026-05-10", "MARQUETTE", "Championnat Nord"), 0)  # idempotent
        self.assertEqual([r.get("raceType") for r in m.road["2026"]], ["Championnat Nord", None])


class CategoryTest(unittest.TestCase):
    def test_normalize_category(self):
        n = pdf_results.normalize_category
        for label, expected in [("30/39ans", "30/39 ans"), ("30-39 ans", "30/39 ans"), ("Masculins 30/39 ans", "30/39 ans"),
                                ("Juniors 17/19 ans", "17/19 ans"), ("Séniors B - 30/39 ans", "Seniors B"),
                                ("Vétérans A - 40/49 ans", "Vétérans A"), ("SeniorA", "Seniors A"),
                                ("4ème Catégorie", "4ème"), ("1ère", "1ère"), ("Juniors", "Juniors"),
                                ("Masculins 60 ans et plus", "60 ans et plus"), ("Féminines", "Féminines"), ("", "")]:
            self.assertEqual(n(label), expected, label)

    def test_sheet_names_use_it(self):
        self.assertEqual(pdf_results.canonical_sheet_name("Masculins 50/59 ans"), "50/59 ans")
        self.assertEqual(pdf_results.canonical_sheet_name("4ème Catégorie"), "4ème")


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
    def test_slugify_like_liquid_latin(self):
        self.assertEqual(site_links.slugify("MAULDE---CHORETTE"), "maulde-chorette")
        self.assertEqual(site_links.slugify("Fécamp-d'Hénin (2)"), "fecamp-d-henin-2")
        self.assertEqual(site_links.slugify("BRUILLE-SAINT-AMAND-"), "bruille-saint-amand")

    def test_post_permalink(self):
        self.assertEqual(site_links.post_permalink("Route", "2026-04-12", "ETROEUNGT"), "/resultats/route/2026-04-12-etroeungt/")
        self.assertEqual(site_links.post_permalink("Cyclo Cross", "2026/11/14", "LES MINES"), "/resultats/cyclo-cross/2026-11-14-les-mines/")


if __name__ == "__main__":
    unittest.main()
