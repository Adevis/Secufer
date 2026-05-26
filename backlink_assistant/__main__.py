import argparse

from . import db
from .server import run


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="backlink_assistant",
        description="Assistant de backlinks legitimes (decouverte, preparation, suivi).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'ecoute.")
    parser.add_argument("--port", type=int, default=8000, help="Port d'ecoute.")
    parser.add_argument("--db", default=db.DEFAULT_DB, help="Fichier de base SQLite.")
    args = parser.parse_args()
    run(host=args.host, port=args.port, db_path=args.db)


if __name__ == "__main__":
    main()
