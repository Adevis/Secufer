"""Tests du suivi des attestations Secufer."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secufer_tracker import (  # noqa: E402
    Attestation,
    AttestationStore,
    Status,
    compute_status,
    expiration_date,
)
from secufer_tracker.cli import main  # noqa: E402


class ExpirationTests(unittest.TestCase):
    def test_expiration_is_three_years_later(self) -> None:
        self.assertEqual(expiration_date(date(2024, 6, 15)), date(2027, 6, 15))

    def test_leap_day_rolls_back_to_28(self) -> None:
        self.assertEqual(expiration_date(date(2020, 2, 29)), date(2023, 2, 28))

    def test_status_thresholds(self) -> None:
        today = date(2025, 1, 1)
        self.assertEqual(compute_status(date(2024, 12, 31), today=today), Status.EXPIRED)
        self.assertEqual(compute_status(date(2025, 1, 15), today=today), Status.URGENT)
        self.assertEqual(compute_status(date(2025, 3, 1), today=today), Status.UPCOMING)
        self.assertEqual(compute_status(date(2026, 1, 1), today=today), Status.VALID)


class AttestationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "attestations.csv"
        self.store = AttestationStore(self.path)

    def _sample(self, **overrides: object) -> Attestation:
        base = dict(
            nom="Durand",
            prenom="Alice",
            email="alice@example.org",
            formation="Habilitation électrique B1V",
            date_delivrance=date(2023, 4, 1),
        )
        base.update(overrides)
        return Attestation(**base)  # type: ignore[arg-type]

    def test_add_and_reload(self) -> None:
        attestation = self.store.add(self._sample())
        reloaded = self.store.all()
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].id, attestation.id)
        self.assertEqual(reloaded[0].date_delivrance, date(2023, 4, 1))
        self.assertEqual(reloaded[0].date_expiration, date(2026, 4, 1))

    def test_renew_updates_expiration(self) -> None:
        attestation = self.store.add(self._sample())
        renewed = self.store.renew(attestation.id, date(2026, 3, 15))
        self.assertEqual(renewed.date_expiration, date(2029, 3, 15))
        self.assertEqual(self.store.all()[0].date_dernier_recyclage, date(2026, 3, 15))

    def test_remove(self) -> None:
        attestation = self.store.add(self._sample())
        self.store.remove(attestation.id)
        self.assertEqual(self.store.all(), [])

    def test_expiring_within(self) -> None:
        self.store.add(self._sample(nom="Far", date_delivrance=date(2024, 1, 1)))
        self.store.add(self._sample(nom="Soon", date_delivrance=date(2022, 6, 1)))
        soon = list(self.store.expiring_within(90, today=date(2025, 4, 1)))
        self.assertEqual([a.nom for a in soon], ["Soon"])

    def test_renew_unknown_id_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.store.renew("inconnu", date(2025, 1, 1))


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "db.csv"

    def test_add_then_list_then_report(self) -> None:
        rc = main(
            [
                "--db",
                str(self.db),
                "add",
                "--nom",
                "Martin",
                "--prenom",
                "Bruno",
                "--formation",
                "SST",
                "--date-delivrance",
                "2023-01-10",
            ]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(len(AttestationStore(self.db).all()), 1)

        report = Path(self.tmp.name) / "rapport.html"
        rc = main(
            [
                "--db",
                str(self.db),
                "--today",
                "2025-12-01",
                "report",
                "--output",
                str(report),
            ]
        )
        self.assertEqual(rc, 0)
        content = report.read_text(encoding="utf-8")
        self.assertIn("Martin", content)
        self.assertIn("centre-secufer.fr", content)


if __name__ == "__main__":
    unittest.main()
