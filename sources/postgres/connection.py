"""Opens connections to the two databases. Every other file gets its connections from here."""

from pathlib import Path

import psycopg
import yaml

ROOT = Path(__file__).resolve().parents[2]  # the project folder
CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text())


def connect_source():
    """The B2B platform database (where the business data comes from)."""
    return psycopg.connect(**CONFIG["source"])


def connect_warehouse():
    """The data warehouse (where the pipeline loads the data)."""
    return psycopg.connect(**CONFIG["warehouse"])
