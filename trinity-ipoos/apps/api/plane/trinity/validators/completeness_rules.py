"""
Trinity Validation Engine — Completeness Rules

For every required field defined in the 5 ICDR JSON schema files,
flag if it's empty/unset, referencing the schema's clause metadata.

Schema files are loaded from plane/trinity/schemas/*.json.
"""

import json
import os
from decimal import Decimal, InvalidOperation

from .flag import FlagResult

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas")

# Maps section_id → (model_accessor_description, is_collection, min_records)
SECTION_CONFIG = {
    "objects_of_issue": {
        "is_collection": False,
        "record_label": "Objects of the Issue",
    },
    "related_party_transactions": {
        "is_collection": True,
        "record_label": "Related Party Transaction",
    },
    "capital_structure": {
        "is_collection": True,
        "record_label": "Shareholder Entry",
    },
    "litigation": {
        "is_collection": True,
        "record_label": "Litigation Entry",
        "allow_empty": True,  # Litigation can legitimately be nil
    },
    "financial_summary": {
        "is_collection": True,
        "record_label": "Financial Year Summary",
        "min_records": 3,
    },
}


def _load_schema(section_id):
    """Load and parse a JSON schema file."""
    filepath = os.path.join(SCHEMA_DIR, f"{section_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)


def _is_field_empty(value):
    """Check if a field value is effectively empty."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (int, float)) and value == 0:
        return False  # Zero is a valid value for numeric fields
    if isinstance(value, Decimal):
        return False  # Any Decimal, including 0, is "set"
    return False


def _check_record_fields(record, fields_schema, section_id, record_label, record_idx=None):
    """
    Check a single record against the schema's field definitions.
    Returns a list of FlagResult for missing required fields.
    """
    flags = []
    record_prefix = f"{record_label} #{record_idx}" if record_idx else record_label

    for field_name, field_def in fields_schema.items():
        if not field_def.get("required", False):
            continue

        value = getattr(record, field_name, None)
        if _is_field_empty(value):
            icdr_clause = field_def.get("icdr_clause", "")
            field_label = field_def.get("label", field_name)

            flags.append(FlagResult(
                rule_id="completeness_required_field",
                severity="blocking",
                section=section_id,
                field_reference=f"{record_prefix}.{field_name}",
                message=(
                    f"Required field '{field_label}' is empty in {record_prefix}. "
                    f"This field is mandated by {icdr_clause} and must be completed "
                    f"before the DRHP can be submitted."
                ),
                regulation_citation=icdr_clause,
                related_data={
                    "field_name": field_name,
                    "field_label": field_label,
                    "icdr_clause": icdr_clause,
                    "icdr_text": field_def.get("icdr_text", ""),
                    "record_label": record_prefix,
                },
            ))

    return flags


def check_objects_of_issue_completeness(objects_of_issue, use_of_proceeds):
    """
    Check completeness of Objects of the Issue section.

    Input:
        - objects_of_issue: ObjectsOfIssue object or None
        - use_of_proceeds: list of UseOfProceeds objects
    Output: List[FlagResult]
    """
    flags = []
    schema = _load_schema("objects_of_issue")
    if schema is None:
        return flags

    if objects_of_issue is None:
        flags.append(FlagResult(
            rule_id="completeness_section_missing",
            severity="blocking",
            section="objects_of_issue",
            field_reference="objects_of_issue",
            message=(
                "Objects of the Issue section has not been started. "
                "This is a mandatory DRHP disclosure section."
            ),
            regulation_citation=schema.get("regulation_reference", ""),
            related_data={"section_id": "objects_of_issue"},
        ))
        return flags

    # Check header fields
    flags.extend(_check_record_fields(
        objects_of_issue,
        schema.get("fields", {}),
        "objects_of_issue",
        "Objects of the Issue",
    ))

    # Check line items
    line_item_fields = schema.get("line_item_fields", {})
    if not use_of_proceeds:
        flags.append(FlagResult(
            rule_id="completeness_no_line_items",
            severity="blocking",
            section="objects_of_issue",
            field_reference="use_of_proceeds",
            message=(
                "No use-of-proceeds line items have been added. At least one "
                "line item specifying how the proceeds will be used is required."
            ),
            regulation_citation="Schedule VI, Part A, Clause 2(1)(b)",
            related_data={"section_id": "objects_of_issue"},
        ))
    else:
        for idx, item in enumerate(use_of_proceeds, 1):
            flags.extend(_check_record_fields(
                item, line_item_fields,
                "objects_of_issue",
                "Use of Proceeds",
                record_idx=idx,
            ))

    return flags


def check_collection_completeness(records, section_id):
    """
    Check completeness for a collection-type section (RPTs, Shareholders,
    Litigation, Financials).

    Input:
        - records: list of model objects
        - section_id: string matching the schema filename
    Output: List[FlagResult]
    """
    flags = []
    schema = _load_schema(section_id)
    if schema is None:
        return flags

    config = SECTION_CONFIG.get(section_id, {})
    record_label = config.get("record_label", section_id)
    allow_empty = config.get("allow_empty", False)
    min_records = config.get("min_records", 1)

    # Check if section has any records
    if not records and not allow_empty:
        flags.append(FlagResult(
            rule_id="completeness_section_empty",
            severity="info" if allow_empty else "warning",
            section=section_id,
            field_reference=section_id,
            message=(
                f"No {record_label} entries have been added. "
                f"{'This section can be disclosed as nil.' if allow_empty else 'Please add at least one entry.'}"
            ),
            regulation_citation=schema.get("regulation_reference", ""),
            related_data={
                "section_id": section_id,
                "record_count": 0,
                "min_required": min_records,
            },
        ))
        return flags

    # Check minimum record count
    if len(records) < min_records and not allow_empty:
        flags.append(FlagResult(
            rule_id="completeness_insufficient_records",
            severity="warning",
            section=section_id,
            field_reference=section_id,
            message=(
                f"Only {len(records)} {record_label} record(s) entered, "
                f"but {min_records} are expected. Please add the remaining entries."
            ),
            regulation_citation=schema.get("regulation_reference", ""),
            related_data={
                "section_id": section_id,
                "record_count": len(records),
                "min_required": min_records,
            },
        ))

    # Check individual record field completeness
    fields_schema = schema.get("fields", {})
    for idx, record in enumerate(records, 1):
        flags.extend(_check_record_fields(
            record, fields_schema, section_id, record_label, record_idx=idx,
        ))

    return flags


def run_completeness_rules(objects_of_issue, use_of_proceeds, rpts,
                           shareholders, litigations, financial_summaries):
    """Run all completeness checks and return combined flags."""
    flags = []

    # Objects of the Issue (special: header + line items)
    flags.extend(check_objects_of_issue_completeness(
        objects_of_issue, use_of_proceeds
    ))

    # Collection sections
    flags.extend(check_collection_completeness(rpts, "related_party_transactions"))
    flags.extend(check_collection_completeness(shareholders, "capital_structure"))
    flags.extend(check_collection_completeness(litigations, "litigation"))
    flags.extend(check_collection_completeness(financial_summaries, "financial_summary"))

    return flags
