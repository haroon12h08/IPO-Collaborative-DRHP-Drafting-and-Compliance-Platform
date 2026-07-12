"""
Trinity Validation Engine — Orchestrator

Loads all section data for an IPO workspace, runs every deterministic rule,
and persists the resulting flags to the database.  Old flags are deleted and
replaced each time so the flag set always reflects the *current* data state.

Usage (from a view):

    from plane.trinity.validators.engine import run_validation
    flags = run_validation(ipo_workspace)
"""

from plane.trinity.models import (
    IPOWorkspace,
    ObjectsOfIssue,
    UseOfProceeds,
    RelatedPartyTransaction,
    ShareholderEntry,
    LitigationEntry,
    FinancialYearSummary,
    ValidationFlag,
)

from .rpt_rules import run_rpt_rules
from .objects_rules import run_objects_rules
from .cross_section_rules import run_cross_section_rules
from .completeness_rules import run_completeness_rules


# ---------------------------------------------------------------------------
# Severity sort key — used for deterministic ordering of the output
# ---------------------------------------------------------------------------
SEVERITY_ORDER = {"blocking": 0, "warning": 1, "info": 2}


def _load_section_data(ipo_workspace):
    """
    Fetch all section data for a given IPO workspace in a single pass.
    Returns a dict of all data objects / querysets needed by the rules.
    """
    # Objects of the Issue (singleton per workspace)
    try:
        objects_of_issue = ObjectsOfIssue.objects.get(
            ipo_workspace=ipo_workspace
        )
    except ObjectsOfIssue.DoesNotExist:
        objects_of_issue = None

    # Use of Proceeds (children of ObjectsOfIssue)
    if objects_of_issue:
        use_of_proceeds = list(
            UseOfProceeds.objects.filter(objects_of_issue=objects_of_issue)
        )
    else:
        use_of_proceeds = []

    # Collection sections — materialise into lists so rules can iterate freely
    rpts = list(
        RelatedPartyTransaction.objects.filter(ipo_workspace=ipo_workspace)
    )
    shareholders = list(
        ShareholderEntry.objects.filter(ipo_workspace=ipo_workspace)
    )
    litigations = list(
        LitigationEntry.objects.filter(ipo_workspace=ipo_workspace)
    )
    financial_summaries = list(
        FinancialYearSummary.objects.filter(ipo_workspace=ipo_workspace)
    )

    return {
        "objects_of_issue": objects_of_issue,
        "use_of_proceeds": use_of_proceeds,
        "rpts": rpts,
        "shareholders": shareholders,
        "litigations": litigations,
        "financial_summaries": financial_summaries,
    }


def _run_all_rules(data):
    """
    Execute every rule module against the loaded data.
    Returns a flat list of FlagResult objects.
    """
    all_flags = []

    # 1) RPT threshold rules
    all_flags.extend(run_rpt_rules(
        data["rpts"],
        data["financial_summaries"],
    ))

    # 2) Objects of the Issue / Use of Proceeds rules
    all_flags.extend(run_objects_rules(
        data["objects_of_issue"],
        data["use_of_proceeds"],
        data["rpts"],
        data["shareholders"],
        data["financial_summaries"],
    ))

    # 3) Cross-section consistency rules
    all_flags.extend(run_cross_section_rules(
        data["shareholders"],
        data["litigations"],
    ))

    # 4) Completeness rules
    all_flags.extend(run_completeness_rules(
        data["objects_of_issue"],
        data["use_of_proceeds"],
        data["rpts"],
        data["shareholders"],
        data["litigations"],
        data["financial_summaries"],
    ))

    return all_flags


def _persist_flags(ipo_workspace, flag_results):
    """
    Delete all existing flags for the workspace and bulk-create the new set.
    Returns the list of created ValidationFlag instances.
    """
    # Hard-delete old flags (not soft-delete — these are ephemeral)
    ValidationFlag.objects.filter(ipo_workspace=ipo_workspace).delete()

    flag_objects = [
        ValidationFlag(
            ipo_workspace=ipo_workspace,
            rule_id=f.rule_id,
            severity=f.severity,
            section=f.section,
            field_reference=f.field_reference,
            message=f.message,
            regulation_citation=f.regulation_citation,
            related_data=f.related_data,
        )
        for f in flag_results
    ]

    if flag_objects:
        ValidationFlag.objects.bulk_create(flag_objects)

    return flag_objects


def run_validation(ipo_workspace):
    """
    Main entry point.  Runs all deterministic validation rules against the
    current data for the given IPO workspace, persists the flags, and returns
    the saved ValidationFlag queryset sorted by severity.

    Args:
        ipo_workspace: An IPOWorkspace instance.

    Returns:
        QuerySet[ValidationFlag] — the freshly created flags, ordered by
        severity (blocking → warning → info), then section, then created_at.
    """
    data = _load_section_data(ipo_workspace)
    flag_results = _run_all_rules(data)

    # Sort by severity before persisting
    flag_results.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.section))

    _persist_flags(ipo_workspace, flag_results)

    # Return the fresh queryset from DB for serialisation
    return ValidationFlag.objects.filter(ipo_workspace=ipo_workspace)
