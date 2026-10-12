"""Runs .sql files in the warehouse."""

from sources.postgres.connection import ROOT


def run_sql_file(warehouse, path):
    """Run every statement in one .sql file."""
    warehouse.execute((ROOT / path).read_text())


def query_sql_file(warehouse, path):
    """Run a .sql file that holds one SELECT and return its rows."""
    return warehouse.execute((ROOT / path).read_text()).fetchall()
