import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import races_registry  # noqa: E402


class RegistryTest(unittest.TestCase):
    def test_round_trip_and_ordering(self):
        reg = races_registry.RaceRegistry()
        reg.set("cx", "2027", "ORCHIES", "2026-10-04", "abc")
        reg.set("cx", "2027", "COMINES", "2026-11-14")
        reg.set("road", "2026", "HASPRES", "2026/03/07")
        reg.set("vtt", "2027", "RAISMES")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "races.json")
            self.assertTrue(reg.save(path))
            self.assertFalse(reg.save(path))  # inchangé : fichier non réécrit
            data = json.load(open(path, encoding="utf8"))
            loaded = races_registry.RaceRegistry.load(path)
        self.assertEqual([r["year"] for r in data["races"]], [2027, 2026])  # saisons récentes d'abord
        self.assertEqual([r["name"] for r in data["races"][0]["cx"]], ["ORCHIES", "COMINES"])  # triées par date
        self.assertEqual(data["races"][1]["road"][0]["date"], "2026-03-07")
        self.assertTrue(loaded.has("cx", 2027, "ORCHIES"))
        self.assertEqual(loaded.sha("cx", "2027", "ORCHIES"), "abc")
        self.assertIsNone(loaded.sha("cx", "2027", "COMINES"))

    def test_touch_date_only_for_known_races(self):
        reg = races_registry.RaceRegistry()
        reg.touch_date("cx", "2027", "INCONNUE", "2026-10-04")
        self.assertFalse(reg.has("cx", "2027", "INCONNUE"))
        reg.set("cx", "2027", "ORCHIES")
        reg.touch_date("cx", "2027", "ORCHIES", "2026/10/04")
        self.assertEqual(reg.entries[("cx", "2027", "ORCHIES")]["date"], "2026-10-04")

    def test_prune_keeps_current_seasons_only(self):
        reg = races_registry.RaceRegistry()
        reg.set("road", "2025", "A")
        reg.set("road", "2026", "B")
        reg.set("cx", "2027", "C")
        reg.prune({"road": "2026", "cx": "2027", "vtt": "2027"})
        self.assertEqual(sorted(k[2] for k in reg.entries), ["B", "C"])


if __name__ == "__main__":
    unittest.main()
