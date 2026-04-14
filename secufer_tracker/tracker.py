"""Cœur du suivi des attestations Secufer.

Les attestations Secufer ont une validité de 3 ans. Ce module fournit :

- la structure :class:`Attestation`,
- le calcul de la date d'expiration et du statut,
- un magasin CSV :class:`AttestationStore` permettant aux RH d'ajouter,
  de lister et de renouveler les attestations.
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator

VALIDITY_YEARS = 3
URGENT_THRESHOLD_DAYS = 30
UPCOMING_THRESHOLD_DAYS = 90

CSV_FIELDS = (
    "id",
    "nom",
    "prenom",
    "email",
    "formation",
    "date_delivrance",
    "date_dernier_recyclage",
    "notes",
)


class Status(str, Enum):
    """Statut d'une attestation vis-à-vis de sa date d'expiration."""

    EXPIRED = "expirée"
    URGENT = "urgent"
    UPCOMING = "à programmer"
    VALID = "valide"


@dataclass
class Attestation:
    """Une attestation délivrée par Secufer."""

    nom: str
    prenom: str
    email: str
    formation: str
    date_delivrance: date
    date_dernier_recyclage: date | None = None
    notes: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def date_reference(self) -> date:
        """Date à partir de laquelle on calcule l'expiration."""
        return self.date_dernier_recyclage or self.date_delivrance

    @property
    def date_expiration(self) -> date:
        return expiration_date(self.date_reference)

    def status(self, today: date | None = None) -> Status:
        return compute_status(self.date_expiration, today=today)

    def days_until_expiration(self, today: date | None = None) -> int:
        today = today or date.today()
        return (self.date_expiration - today).days


def expiration_date(reference: date) -> date:
    """Renvoie la date d'expiration pour une date de référence donnée."""
    try:
        return reference.replace(year=reference.year + VALIDITY_YEARS)
    except ValueError:
        # 29 février : on retombe sur le 28 février de l'année cible.
        return reference.replace(month=2, day=28, year=reference.year + VALIDITY_YEARS)


def compute_status(expiration: date, today: date | None = None) -> Status:
    today = today or date.today()
    delta = (expiration - today).days
    if delta < 0:
        return Status.EXPIRED
    if delta <= URGENT_THRESHOLD_DAYS:
        return Status.URGENT
    if delta <= UPCOMING_THRESHOLD_DAYS:
        return Status.UPCOMING
    return Status.VALID


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return date.fromisoformat(value)


def _format_date(value: date | None) -> str:
    return value.isoformat() if value else ""


class AttestationStore:
    """Persiste les attestations dans un fichier CSV."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _load(self) -> list[Attestation]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            return [
                Attestation(
                    id=row["id"],
                    nom=row["nom"],
                    prenom=row["prenom"],
                    email=row.get("email", ""),
                    formation=row["formation"],
                    date_delivrance=_parse_date(row["date_delivrance"]),  # type: ignore[arg-type]
                    date_dernier_recyclage=_parse_date(row.get("date_dernier_recyclage", "")),
                    notes=row.get("notes", ""),
                )
                for row in reader
            ]

    def _save(self, attestations: Iterable[Attestation]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for attestation in attestations:
                row = asdict(attestation)
                row["date_delivrance"] = _format_date(attestation.date_delivrance)
                row["date_dernier_recyclage"] = _format_date(attestation.date_dernier_recyclage)
                writer.writerow(row)

    # --- API publique --------------------------------------------------

    def all(self) -> list[Attestation]:
        return self._load()

    def add(self, attestation: Attestation) -> Attestation:
        attestations = self._load()
        if any(a.id == attestation.id for a in attestations):
            raise ValueError(f"identifiant déjà utilisé : {attestation.id}")
        attestations.append(attestation)
        self._save(attestations)
        return attestation

    def renew(self, attestation_id: str, recyclage_date: date) -> Attestation:
        attestations = self._load()
        for attestation in attestations:
            if attestation.id == attestation_id:
                attestation.date_dernier_recyclage = recyclage_date
                self._save(attestations)
                return attestation
        raise KeyError(f"attestation introuvable : {attestation_id}")

    def remove(self, attestation_id: str) -> None:
        attestations = self._load()
        kept = [a for a in attestations if a.id != attestation_id]
        if len(kept) == len(attestations):
            raise KeyError(f"attestation introuvable : {attestation_id}")
        self._save(kept)

    def expiring_within(
        self, days: int, today: date | None = None
    ) -> Iterator[Attestation]:
        today = today or date.today()
        horizon = today + timedelta(days=days)
        for attestation in self._load():
            if attestation.date_expiration <= horizon:
                yield attestation
