import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import upload_photos  # noqa: E402


class UploadPhotosTest(unittest.TestCase):
    def test_extract_url_parts(self):
        parts = upload_photos.extract_url_parts("https://teamspecializedlille.cc/resultats/route/2026-05-01-pont-sur-sambre/")
        self.assertEqual((parts["year"], parts["month"], parts["day"], parts["race_type"], parts["route_name"]),
                         ("2026", "05", "01", "Route", "pont-sur-sambre"))
        self.assertEqual(parts["permalink"], "/resultats/route/2026-05-01-pont-sur-sambre/")

    def test_find_post_by_permalink(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "2026-05-01-RoutePONT-SUR-SAMBRE.md"), "w", encoding="utf8") as post:
                post.write("---\nlayout: post\npermalink: /resultats/route/2026-05-01-pont-sur-sambre/\n---\n")
            found = upload_photos.find_post_path("/resultats/route/2026-05-01-pont-sur-sambre/", tmp)
            self.assertTrue(found.endswith("2026-05-01-RoutePONT-SUR-SAMBRE.md"))
            self.assertIsNone(upload_photos.find_post_path("/resultats/route/2026-05-02-autre/", tmp))


if __name__ == "__main__":
    unittest.main()
