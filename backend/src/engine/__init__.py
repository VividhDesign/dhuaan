"""Dhuaan smoke-forecast engine: satellite fires + winds -> smoke trajectories -> Smoke Index.

Pure Python + numpy. No AWS imports, so it runs the same locally, in tests and in Lambda.
"""
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=None)
def load_data(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def param(params: dict, key: str):
    """Parameters are either plain values or {"value": ..., "source": ...} records."""
    v = params[key]
    return v["value"] if isinstance(v, dict) and "value" in v else v
