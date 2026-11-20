import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import notifications  # noqa: E402
import parse_results  # noqa: E402
import team_members  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "lillers_cx.pdf")
POST = "2026-10-18-CycloCrossLILLERS.md"


class RefreshTest(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "python_scripts"))
        os.makedirs(os.path.join(self.tmp.name, "_posts"))
        os.chdir(os.path.join(self.tmp.name, "python_scripts"))
        with open("../_posts/" + POST, "w", encoding="utf8") as post:
            post.write("---\nlayout: post\ntitle: Cyclo Cross - LILLERS - 2027\ndate: 2026-10-18\ncategory: Cyclo Cross\n"
                       "tags: cyclo-cross\nimage: x.png\nimages:\n  - path: assets/a.jpg\n    photographer: P\n---\n\nancien\n")
        member = team_members.TeamMember("DERASSE DAVID")
        member.upsert_result("cx", "2027", team_members.make_result("2026-10-18", "LILLERS", "1ère", 99))
        self.team = {"DERASSE DAVID": member}
        self.parser = parse_results.ParseResults(self.team, {})
        self.parser.used_pdfs = set()
        self.parser.race_type, self.parser.race_name = "Cyclo Cross", "LILLERS"
        self.parser.race_year, self.parser.race_date = "2027", "2026/10/18"
        self.parser.fetch_race_pdf = lambda href, name: (FIXTURE, False)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def refresh(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.parser.refresh_race("x", "LILLERS", "2027")
        return out.getvalue()

    def test_changed_pdf_updates_results_and_keeps_photos(self):
        out = self.refresh()
        self.assertIn("[MAJ]", out)
        self.assertNotIn("[NEW POST]", out)
        results = self.team["DERASSE DAVID"].cx["2027"]
        self.assertEqual(len(results), 1)  # relecture : pas de doublon
        self.assertNotEqual(results[0]["rank"], 99)
        self.assertIsNotNone(results[0]["participants"])
        content = open("../_posts/" + POST, encoding="utf8").read()
        self.assertIn("images:\n  - path: assets/a.jpg\n    photographer: P", content)
        self.assertNotIn("ancien", content)

    def test_same_pdf_is_not_reprocessed(self):
        self.refresh()
        self.team["DERASSE DAVID"].cx["2027"][0]["rank"] = 99  # modifié à la main
        self.assertEqual(self.refresh(), "")
        self.assertEqual(self.team["DERASSE DAVID"].cx["2027"][0]["rank"], 99)

    def test_failure_keeps_previous_results(self):
        self.parser.parse_results_race_pdf = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        out = self.refresh()
        self.assertIn("[ERROR]", out)
        self.assertEqual(self.team["DERASSE DAVID"].cx["2027"][0]["rank"], 99)


class SeasonsTest(unittest.TestCase):
    def test_default_seasons(self):
        import datetime
        d = parse_results.default_seasons
        # route : année civile, même quand le CX/VTT est déjà passé à la saison suivante (août-septembre)
        self.assertEqual(d(datetime.date(2026, 9, 20)), {"calResVTT.php": "2027", "calResCross.php": "2027",
                                                         "calResRoute.php": "2026"})
        self.assertEqual(d(datetime.date(2026, 12, 20))["calResRoute.php"], "2026")
        self.assertEqual(d(datetime.date(2027, 1, 5)), {"calResVTT.php": "2027", "calResCross.php": "2027",
                                                        "calResRoute.php": "2027"})
        self.assertEqual(d(datetime.date(2026, 3, 1))["calResCross.php"], "2026")
        self.assertEqual(d(datetime.date(2026, 9, 1), "2030", "2029")["calResRoute.php"], "2029")

    def test_each_calendar_uses_its_own_season(self):
        seen = []
        parser = parse_results.ParseResults({}, {})
        parser.fetch_calendar = lambda page, season: (seen.append((page, season)) or "")
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "python_scripts"))
            os.makedirs(os.path.join(tmp, "_data"))
            old = os.getcwd()
            os.chdir(os.path.join(tmp, "python_scripts"))
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    parser.generate_results({"calResVTT.php": "2027", "calResCross.php": "2027",
                                             "calResRoute.php": "2026"})
            finally:
                os.chdir(old)
        self.assertEqual(sorted(seen), [("calResCross.php", "2027"), ("calResRoute.php", "2026"),
                                        ("calResVTT.php", "2027")])


class NotificationsTest(unittest.TestCase):
    def test_describe_post(self):
        self.assertEqual(notifications.describe_post("2026-04-26-RouteMAULDE---CHORETTE.md"),
                         ("Route", "MAULDE CHORETTE", "26 avril"))
        self.assertEqual(notifications.describe_post("2026-11-15-CycloCrossRAISMES.md"),
                         ("Cyclo Cross", "RAISMES", "15 novembre"))
        self.assertIsNone(notifications.describe_post("nimporte-quoi.md"))

    def test_get_new_posts(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf8") as f:
            f.write("[MAJ] post mis à jour : a.md\n[NEW POST] : 2026-11-15-VTTRAISMES.md\nautre\n")
        try:
            self.assertEqual(notifications.get_new_posts(f.name), ["2026-11-15-VTTRAISMES.md"])
        finally:
            os.unlink(f.name)

    def test_post_url_from_permalink(self):
        url = notifications.site_links.post_url("2026-05-10-RouteMARQUETTE-EN-OSTREVENT.md")
        self.assertEqual(url, "/resultats/route/2026-05-10-marquette-en-ostrevent/")


if __name__ == "__main__":
    unittest.main()
