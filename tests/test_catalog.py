import unittest

from backlink_assistant import catalog


class NormalizeKeywordsTests(unittest.TestCase):
    def test_strips_accents_and_stopwords(self):
        kw = catalog.normalize_keywords("Le Développement de logiciels et SaaS")
        self.assertIn("developpement", kw)
        self.assertIn("logiciels", kw)
        self.assertIn("saas", kw)
        self.assertNotIn("le", kw)
        self.assertNotIn("et", kw)

    def test_dedupes_and_drops_short_tokens(self):
        kw = catalog.normalize_keywords("seo SEO seo go")
        self.assertEqual(kw.count("seo"), 1)
        self.assertNotIn("go", kw)


class MatchDirectoriesTests(unittest.TestCase):
    def test_tech_keywords_surface_niche_platforms(self):
        results = catalog.match_directories(["developpement", "logiciel", "saas"])
        slugs = [r["slug"] for r in results]
        self.assertIn("dev-to", slugs)
        # dev.to (niche pertinent) doit primer sur un annuaire generaliste neutre
        self.assertGreater(
            next(r["score"] for r in results if r["slug"] == "dev-to"),
            next(r["score"] for r in results if r["slug"] == "wordpress-com"),
        )

    def test_irrelevant_niche_is_filtered_out(self):
        results = catalog.match_directories(["plomberie", "chauffage"])
        slugs = [r["slug"] for r in results]
        self.assertNotIn("dev-to", slugs)
        # les plateformes generalistes/locales restent proposees
        self.assertIn("google-business-profile", slugs)

    def test_results_sorted_by_score_desc(self):
        results = catalog.match_directories(["saas", "startup"])
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_country_bonus(self):
        fr = catalog.score_directory(catalog.get_directory("pages-jaunes"), [], "FR")
        us = catalog.score_directory(catalog.get_directory("pages-jaunes"), [], "US")
        self.assertGreater(fr, us)


if __name__ == "__main__":
    unittest.main()
