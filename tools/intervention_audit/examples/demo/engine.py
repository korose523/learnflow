"""Toy source for a read-only audit demonstration, with no user data."""
from mechanism_registry import Effect


def make_demo():
    return Effect(mechanism_id="DEMO-01", message="Illustrative candidate")
