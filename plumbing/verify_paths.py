"""Shared path shim so plumbing scripts agree on the repo root."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
