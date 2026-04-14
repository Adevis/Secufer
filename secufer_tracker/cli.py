"""Interface en ligne de commande pour le suivi des attestations Secufer."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from html import escape
from pathlib import Path

from .tracker import (
    Attestation,
    AttestationStore,
    Status,
    UPCOMING_THRESHOLD_DAYS,
)

DEFAULT_DB = Path("attestations.csv")

STATUS_LABEL = {
    Status.EXPIRED: "EXPIRÉE",
    Status.URGENT: "URGENT",
    Status.UPCOMING: "À PROGRAMMER",
    Status.VALID: "valide",
}


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date invalide (attendu YYYY-MM-DD) : {value}") from exc


def _format_row(attestation: Attestation, today: date) -> str:
    status = attestation.status(today=today)
    days = attestation.days_until_expiration(today=today)
    jours = f"{days:+d} j"
    return (
        f"{attestation.id}  "
        f"{attestation.nom:<15.15} {attestation.prenom:<12.12} "
        f"{attestation.formation:<25.25} "
        f"délivrée {attestation.date_delivrance.isoformat()}  "
        f"expire {attestation.date_expiration.isoformat()} ({jours})  "
        f"[{STATUS_LABEL[status]}]"
    )


def cmd_add(args: argparse.Namespace) -> int:
    store = AttestationStore(args.db)
    attestation = Attestation(
        nom=args.nom,
        prenom=args.prenom,
        email=args.email or "",
        formation=args.formation,
        date_delivrance=args.date_delivrance,
        notes=args.notes or "",
    )
    store.add(attestation)
    print(f"Attestation ajoutée (id={attestation.id}) ; expire le {attestation.date_expiration.isoformat()}.")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    store = AttestationStore(args.db)
    today = args.today or date.today()
    attestations = sorted(store.all(), key=lambda a: a.date_expiration)
    if not attestations:
        print("Aucune attestation enregistrée.")
        return 0
    for attestation in attestations:
        print(_format_row(attestation, today))
    return 0


def cmd_expiring(args: argparse.Namespace) -> int:
    store = AttestationStore(args.db)
    today = args.today or date.today()
    attestations = sorted(
        store.expiring_within(args.days, today=today),
        key=lambda a: a.date_expiration,
    )
    if not attestations:
        print(f"Aucune attestation n'expire dans les {args.days} prochains jours.")
        return 0
    print(f"Attestations à recycler dans les {args.days} prochains jours :")
    for attestation in attestations:
        print(_format_row(attestation, today))
    return 0


def cmd_renew(args: argparse.Namespace) -> int:
    store = AttestationStore(args.db)
    attestation = store.renew(args.id, args.date_recyclage)
    print(
        f"Recyclage enregistré pour {attestation.prenom} {attestation.nom}. "
        f"Nouvelle expiration : {attestation.date_expiration.isoformat()}."
    )
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    store = AttestationStore(args.db)
    store.remove(args.id)
    print(f"Attestation {args.id} supprimée.")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    store = AttestationStore(args.db)
    today = args.today or date.today()
    attestations = sorted(store.all(), key=lambda a: a.date_expiration)
    html = _render_html(attestations, today)
    args.output.write_text(html, encoding="utf-8")
    print(f"Rapport HTML généré : {args.output}")
    return 0


def _render_html(attestations: list[Attestation], today: date) -> str:
    rows = []
    for attestation in attestations:
        status = attestation.status(today=today)
        rows.append(
            "<tr class='{cls}'>"
            "<td>{nom}</td><td>{prenom}</td><td>{email}</td>"
            "<td>{formation}</td><td>{delivrance}</td>"
            "<td>{expiration}</td><td>{jours:+d}</td><td>{statut}</td>"
            "</tr>".format(
                cls=status.name.lower(),
                nom=escape(attestation.nom),
                prenom=escape(attestation.prenom),
                email=escape(attestation.email),
                formation=escape(attestation.formation),
                delivrance=attestation.date_delivrance.isoformat(),
                expiration=attestation.date_expiration.isoformat(),
                jours=attestation.days_until_expiration(today=today),
                statut=STATUS_LABEL[status],
            )
        )
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Suivi des attestations Secufer ({today.isoformat()})</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
h1 {{ margin-bottom: .25rem; }}
p.meta {{ color: #666; margin-top: 0; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: .4rem .6rem; text-align: left; }}
th {{ background: #f2f4f7; }}
tr.expired td {{ background: #fde2e1; }}
tr.urgent td {{ background: #fde7c7; }}
tr.upcoming td {{ background: #fff6cc; }}
tr.valid td {{ background: #e6f4ea; }}
footer {{ margin-top: 2rem; font-size: .9rem; color: #666; }}
a {{ color: #0b5fff; }}
</style>
</head>
<body>
<h1>Suivi des attestations Secufer</h1>
<p class="meta">Rapport généré le {today.isoformat()}. Validité : {3} ans.</p>
<table>
<thead>
<tr><th>Nom</th><th>Prénom</th><th>Email</th><th>Formation</th>
<th>Délivrance</th><th>Expiration</th><th>Jours restants</th><th>Statut</th></tr>
</thead>
<tbody>
{''.join(rows) if rows else '<tr><td colspan="8">Aucune attestation enregistrée.</td></tr>'}
</tbody>
</table>
<footer>
Plus d'informations sur les formations et recyclages :
<a href="https://centre-secufer.fr">centre-secufer.fr</a>.
</footer>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secufer-tracker",
        description="Suivi RH des attestations Secufer (validité 3 ans) et de leurs recyclages.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Fichier CSV de stockage (défaut : {DEFAULT_DB}).",
    )
    parser.add_argument(
        "--today",
        type=_parse_iso_date,
        default=None,
        help="Date de référence (utile pour les tests). Par défaut : aujourd'hui.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Ajouter une attestation.")
    p_add.add_argument("--nom", required=True)
    p_add.add_argument("--prenom", required=True)
    p_add.add_argument("--email", default="")
    p_add.add_argument("--formation", required=True)
    p_add.add_argument("--date-delivrance", dest="date_delivrance", required=True, type=_parse_iso_date)
    p_add.add_argument("--notes", default="")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="Lister toutes les attestations.")
    p_list.set_defaults(func=cmd_list)

    p_exp = sub.add_parser("expiring", help="Lister les attestations qui expirent bientôt.")
    p_exp.add_argument("--days", type=int, default=UPCOMING_THRESHOLD_DAYS)
    p_exp.set_defaults(func=cmd_expiring)

    p_renew = sub.add_parser("renew", help="Enregistrer un recyclage.")
    p_renew.add_argument("--id", required=True)
    p_renew.add_argument(
        "--date-recyclage",
        dest="date_recyclage",
        required=True,
        type=_parse_iso_date,
    )
    p_renew.set_defaults(func=cmd_renew)

    p_remove = sub.add_parser("remove", help="Supprimer une attestation.")
    p_remove.add_argument("--id", required=True)
    p_remove.set_defaults(func=cmd_remove)

    p_report = sub.add_parser("report", help="Générer un rapport HTML.")
    p_report.add_argument("--output", type=Path, default=Path("rapport_attestations.html"))
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
