"""
Trinity Validation Engine — Flag Data Structure

A FlagResult is a plain dataclass capturing one validation finding.
It is used as the intermediate representation between rule functions and
the database model (ValidationFlag).
"""

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FlagResult:
    """
    One validation flag produced by a deterministic rule.

    Attributes:
        rule_id:              Machine-readable rule identifier.
        severity:             "blocking" | "warning" | "info"
        section:              DRHP section this flag belongs to.
        field_reference:      Specific field(s) or record(s) involved.
        message:              Human-readable description.
        regulation_citation:  ICDR clause / SEBI regulation reference.
        related_data:         Dict with the actual figures that triggered the flag.
    """

    rule_id: str
    severity: str  # "blocking", "warning", "info"
    section: str
    field_reference: str
    message: str
    regulation_citation: str
    related_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
