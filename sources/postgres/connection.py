"""Opens connections to the two databases. Every other file gets its connections from here."""

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import yaml

ROOT = Path(__file__).resolve().parents[2]  # the project folder
CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text())
LOG_FILE = Path(CONFIG["log_file"]).expanduser()  # the web server log

# Which warehouse to use: "dev" (the default) or "prod".  Example:  B2B_ENV=prod python run.py
ENV = os.environ.get("B2B_ENV", "dev")


def local_now():
    """The current time in the business time zone (config.yaml), not in the computer's own time zone."""
    return datetime.now(ZoneInfo(CONFIG["timezone"]))


def connect_source():
    """The B2B platform database (where the business data comes from)."""
    return psycopg.connect(**CONFIG["source"])


def connect_warehouse():
    """The data warehouse of the current environment (dev or prod)."""
    return psycopg.connect(**CONFIG[f"warehouse_{ENV}"])
