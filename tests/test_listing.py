import unittest

from backlink_assistant import catalog, listing


class ListingTests(unittest.TestCase):
    def test_short_description_truncates_on_word_boundary(self):
        text = "mot " * 100
        short = listing.short_description(text, limit=20)
        self.assertLessEqual(len(short), 20)
        self.assertTrue(short.endswith("…"))
        self.assertNotIn("  ", short)

    def test_short_description_keeps_short_text(self):
        self.assertEqual(listing.short_description("Court"), "Court")

    def test_generate_listing_fields(self):
        site = {
            "name": "Centre Secufer", "url": "https://centre-secufer.fr",
            "description": "Formations sécurité et habilitations.",
            "keywords": "formation, securite", "category": "Formation",
            "city": "Lyon", "country": "FR",
        }
        directory = catalog.get_directory("dev-to")
        out = listing.generate_listing(site, directory)
        self.assertEqual(out["fields"]["title"], "Centre Secufer")
        self.assertEqual(out["fields"]["url"], "https://centre-secufer.fr")
        self.assertTrue(out["hints"])

    def test_api_directory_hint_mentions_automation(self):
        site = {"name": "X", "url": "https://x.fr", "description": "d"}
        out = listing.generate_listing(site, catalog.get_directory("dev-to"))
        self.assertTrue(any("API" in h for h in out["hints"]))

    def test_manual_directory_hint_mentions_manual(self):
        site = {"name": "X", "url": "https://x.fr", "description": "d"}
        out = listing.generate_listing(site, catalog.get_directory("pages-jaunes"))
        self.assertTrue(any("manuelle" in h.lower() for h in out["hints"]))


if __name__ == "__main__":
    unittest.main()
