"""Illustrative local fixture only; not an application intervention registry."""
from dataclasses import dataclass


@dataclass
class Effect:
    mechanism_id: str
    message: str
