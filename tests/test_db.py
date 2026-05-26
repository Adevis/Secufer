import unittest

from backlink_assistant import db


class DbTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_db(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_add_and_get_site(self):
        site_id = db.add_site(self.conn, name="Mon Site", url="https://exemple.fr",
                              keywords="seo, web")
        site = db.get_site(self.conn, site_id)
        self.assertEqual(site["name"], "Mon Site")
        self.assertEqual(site["country"], "FR")  # defaut

    def test_add_site_requires_name_and_url(self):
        with self.assertRaises(ValueError):
            db.add_site(self.conn, name="", url="")

    def test_submission_upsert_and_status_cycle(self):
        site_id = db.add_site(self.conn, name="S", url="https://s.fr")
        first = db.set_submission(self.conn, site_id, "dev-to", status="todo")
        self.assertEqual(first["status"], "todo")
        self.assertEqual(first["submitted_at"], "")

        submitted = db.set_submission(self.conn, site_id, "dev-to", status="submitted")
        self.assertEqual(submitted["status"], "submitted")
        self.assertTrue(submitted["submitted_at"])  # date posee

        # un seul enregistrement par (site, annuaire)
        self.assertEqual(len(db.list_submissions(self.conn, site_id)), 1)

    def test_invalid_status_rejected(self):
        site_id = db.add_site(self.conn, name="S", url="https://s.fr")
        with self.assertRaises(ValueError):
            db.set_submission(self.conn, site_id, "dev-to", status="bidon")

    def test_delete_site_cascades_submissions(self):
        site_id = db.add_site(self.conn, name="S", url="https://s.fr")
        db.set_submission(self.conn, site_id, "dev-to", status="submitted")
        self.assertTrue(db.delete_site(self.conn, site_id))
        self.assertEqual(db.list_submissions(self.conn, site_id), [])


if __name__ == "__main__":
    unittest.main()
