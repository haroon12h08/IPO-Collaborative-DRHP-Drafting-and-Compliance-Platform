"""
Trinity Validation Engine — Objects of the Issue / Use of Proceeds Rules

Rules based on SEBI ICDR Regulations 2018, Chapter IX, Schedule VI, Part A,
Clause 2(1) and SEBI Consultation Paper on SME Segment Framework (Nov 2024).

Key rule sources:
- GCP cap: SEBI Consultation Paper Nov 2024, Section 3.1 (proposed: 10% or ₹10 cr,
  whichever is lower; existing guideline was 25% but is being tightened for SMEs).
- Debt repayment to promoter prohibition: SEBI Consultation Paper Nov 2024,
  Section 3.3 — proposed prohibition on using IPO proceeds to repay
  promoter/promoter-group loans.
- Working capital disproportionality: SEBI Consultation Paper Nov 2024,
  Section 3.1 — enhanced scrutiny of working capital requirements.

All amounts in ₹ Lakhs.
"""

from decimal import Decimal

from .flag import FlagResult

# Thresholds
GCP_PERCENTAGE_CAP = Decimal("0.10")       # 10% of total fresh issue
GCP_ABSOLUTE_CAP_LAKHS = Decimal("1000")   # ₹10 crore
WORKING_CAPITAL_GROWTH_MULTIPLIER = 3      # Flag if WC > 3x avg annual revenue growth
MIN_JUSTIFICATION_LENGTH = 20              # Characters — below this is "empty"


def check_debt_repayment_to_promoter(use_of_proceeds, rpts, shareholders):
    """
    Rule: debt_repayment_to_promoter

    Flag if any use-of-proceeds line item categorized as "debt_repayment"
    references a promoter or promoter-group entity.
    
    1. If `repayment_counterparty_id` is set, we check if the referenced
       ShareholderEntry or RelatedPartyTransaction is categorized as promoter
       or promoter_group. If so, flags a BLOCKING error.
    2. If `repayment_counterparty_id` is NOT set, we check the legacy text-based
       substring matching against promoter names as a WARNING fallback.

    Input:
        - use_of_proceeds: list of UseOfProceeds objects
        - rpts: list of RelatedPartyTransaction objects
        - shareholders: list of ShareholderEntry objects
    Output: List[FlagResult]
    """
    flags = []

    # Map IDs to objects for fast lookup (handling both string and UUID key formats)
    rpt_by_id = {str(rpt.id): rpt for rpt in rpts if rpt.id}
    sh_by_id = {str(sh.id): sh for sh in shareholders if sh.id}

    # Collect all promoter/promoter-group names (lowercased for fallback matching)
    promoter_names = set()
    for rpt in rpts:
        if rpt.relationship_type in ("promoter", "promoter_group"):
            promoter_names.add(rpt.related_party_name.strip().lower())
    for sh in shareholders:
        if sh.category in ("promoter", "promoter_group"):
            promoter_names.add(sh.shareholder_name.strip().lower())

    for item in use_of_proceeds:
        if item.category != "debt_repayment":
            continue

        structured_match = False
        matched_party_name = None
        counterparty_id = item.repayment_counterparty_id

        # 1. Check structured reference first
        if counterparty_id:
            cid_str = str(counterparty_id)
            rpt_match = rpt_by_id.get(cid_str)
            if rpt_match:
                if rpt_match.relationship_type in ("promoter", "promoter_group"):
                    structured_match = True
                    matched_party_name = rpt_match.related_party_name
            
            sh_match = sh_by_id.get(cid_str)
            if sh_match:
                if sh_match.category in ("promoter", "promoter_group"):
                    structured_match = True
                    matched_party_name = sh_match.shareholder_name

            if structured_match:
                flags.append(FlagResult(
                    rule_id="debt_repayment_to_promoter",
                    severity="blocking",
                    section="objects_of_issue",
                    field_reference="use_of_proceeds.repayment_counterparty_id",
                    message=(
                        f"Debt repayment line item (₹{item.amount:,.2f} lakhs) "
                        f"is structured to repay promoter/promoter-group entity "
                        f"'{matched_party_name}' (ID: {counterparty_id}). "
                        f"SEBI's proposed framework prohibits use of IPO proceeds "
                        f"for repayment of loans from promoters or promoter-group "
                        f"entities in SME IPOs."
                    ),
                    regulation_citation=(
                        "SEBI ICDR 2018, Schedule VI, Part A, Clause 2(1)(b); "
                        "SEBI Consultation Paper on SME Framework (Nov 2024), "
                        "Section 3.3 — Prohibition on Promoter Loan Repayment"
                    ),
                    related_data={
                        "line_item_category": "debt_repayment",
                        "line_item_amount_lakhs": str(item.amount),
                        "repayment_counterparty_id": str(counterparty_id),
                        "matched_promoter_name": matched_party_name,
                        "justification_snippet": (item.justification or "")[:200],
                    },
                ))

        # 2. String-matching fallback for legacy/unstructured data
        else:
            if promoter_names:
                justification_lower = (item.justification or "").lower()
                matched_names = [
                    name for name in promoter_names
                    if name and name in justification_lower
                ]

                if matched_names:
                    flags.append(FlagResult(
                        rule_id="debt_repayment_to_promoter",
                        severity="warning",
                        section="objects_of_issue",
                        field_reference="use_of_proceeds.justification",
                        message=(
                            f"Debt repayment line item (₹{item.amount:,.2f} lakhs) "
                            f"has no structured counterparty link, but its justification "
                            f"references promoter/promoter-group name(s): "
                            f"{', '.join(repr(n) for n in matched_names)}. "
                            f"Please link this line item to a structured shareholder or related party entry "
                            f"to confirm. SEBI's proposed framework prohibits use of IPO proceeds "
                            f"for repayment of promoter loans."
                        ),
                        regulation_citation=(
                            "SEBI ICDR 2018, Schedule VI, Part A, Clause 2(1)(b); "
                            "SEBI Consultation Paper on SME Framework (Nov 2024), "
                            "Section 3.3 — Prohibition on Promoter Loan Repayment"
                        ),
                        related_data={
                            "line_item_category": "debt_repayment",
                            "line_item_amount_lakhs": str(item.amount),
                            "matched_promoter_names": sorted(matched_names),
                            "justification_snippet": (item.justification or "")[:200],
                        },
                    ))

    return flags


def check_gcp_threshold(objects_of_issue, use_of_proceeds):
    """
    Rule: gcp_threshold

    Flag if "General Corporate Purposes" (GCP) amount exceeds the LOWER of:
      - 10% of total fresh issue amount, OR
      - ₹10 crore (₹1,000 lakhs)

    Input:
        - objects_of_issue: ObjectsOfIssue object (or None)
        - use_of_proceeds: list of UseOfProceeds objects
    Output: List[FlagResult]
    """
    flags = []

    if objects_of_issue is None or objects_of_issue.fresh_issue_amount is None:
        return flags

    fresh_issue = objects_of_issue.fresh_issue_amount
    if fresh_issue <= 0:
        return flags

    # Sum all GCP line items
    gcp_total = sum(
        item.amount
        for item in use_of_proceeds
        if item.category == "general_corporate_purposes"
    )

    if gcp_total <= 0:
        return flags

    # Threshold is the LOWER of 10% of fresh issue or ₹10 crore
    percentage_cap = fresh_issue * GCP_PERCENTAGE_CAP
    effective_cap = min(percentage_cap, GCP_ABSOLUTE_CAP_LAKHS)
    gcp_percentage = (gcp_total / fresh_issue) * 100

    if gcp_total > effective_cap:
        cap_description = (
            f"₹{GCP_ABSOLUTE_CAP_LAKHS:,.0f} lakhs (₹10 crore)"
            if effective_cap == GCP_ABSOLUTE_CAP_LAKHS
            else f"10% of fresh issue (₹{percentage_cap:,.2f} lakhs)"
        )
        flags.append(FlagResult(
            rule_id="gcp_threshold",
            severity="blocking",
            section="objects_of_issue",
            field_reference="use_of_proceeds.category=general_corporate_purposes",
            message=(
                f"General Corporate Purposes allocation is ₹{gcp_total:,.2f} lakhs "
                f"({gcp_percentage:.1f}% of fresh issue), which exceeds the cap of "
                f"{cap_description}. Under SEBI's proposed SME framework, GCP is "
                f"capped at 10% of issue size or ₹10 crore, whichever is lower."
            ),
            regulation_citation=(
                "SEBI ICDR 2018, Schedule VI, Part A, Clause 2(1); "
                "SEBI Consultation Paper on SME Framework (Nov 2024), "
                "Section 3.1 — GCP Cap for SME IPOs"
            ),
            related_data={
                "gcp_amount_lakhs": str(gcp_total),
                "fresh_issue_amount_lakhs": str(fresh_issue),
                "gcp_percentage": f"{gcp_percentage:.2f}",
                "effective_cap_lakhs": str(effective_cap),
                "percentage_cap_lakhs": str(percentage_cap),
                "absolute_cap_lakhs": str(GCP_ABSOLUTE_CAP_LAKHS),
            },
        ))

    return flags


def check_working_capital_disproportionate(use_of_proceeds, financial_summaries):
    """
    Rule: working_capital_disproportionate

    Flag if the working capital use-of-proceeds amount is disproportionate
    relative to the company's revenue growth trajectory (last 3 FYs), AND the
    justification text is empty or insufficient.

    "Disproportionate" is defined as: working capital amount exceeds 3× the
    average annual revenue increase over the reported financial years.

    Input:
        - use_of_proceeds: list of UseOfProceeds objects
        - financial_summaries: list of FinancialYearSummary objects
    Output: List[FlagResult]
    """
    flags = []

    # Get working capital line items with insufficient justification
    wc_items = [
        item for item in use_of_proceeds
        if item.category == "working_capital"
        and len((item.justification or "").strip()) < MIN_JUSTIFICATION_LENGTH
    ]

    if not wc_items:
        return flags

    # Calculate average annual revenue growth from financial summaries
    summaries = sorted(financial_summaries, key=lambda s: s.financial_year)
    if len(summaries) < 2:
        return flags  # Need at least 2 years to compute growth

    revenues = [s.revenue for s in summaries]
    # Average annual increase in absolute terms
    total_increase = revenues[-1] - revenues[0]
    years_span = len(revenues) - 1
    avg_annual_increase = total_increase / years_span if years_span > 0 else Decimal("0")

    # If revenue is declining or flat, any substantial WC ask is suspect
    # Use a minimum baseline of 1% of latest revenue for comparison
    if avg_annual_increase <= 0:
        baseline = revenues[-1] * Decimal("0.01")  # 1% of latest revenue
    else:
        baseline = avg_annual_increase

    for item in wc_items:
        if baseline > 0 and item.amount > baseline * WORKING_CAPITAL_GROWTH_MULTIPLIER:
            multiplier = item.amount / baseline if baseline > 0 else Decimal("0")
            flags.append(FlagResult(
                rule_id="working_capital_disproportionate",
                severity="warning",
                section="objects_of_issue",
                field_reference="use_of_proceeds.category=working_capital",
                message=(
                    f"Working capital allocation of ₹{item.amount:,.2f} lakhs is "
                    f"{multiplier:.1f}× the average annual revenue increase "
                    f"(₹{baseline:,.2f} lakhs/year), suggesting a disproportionate "
                    f"ask relative to the company's growth trajectory. The "
                    f"justification provided is empty or insufficient "
                    f"({len((item.justification or '').strip())} chars). "
                    f"Please provide a detailed rationale."
                ),
                regulation_citation=(
                    "SEBI ICDR 2018, Schedule VI, Part A, Clause 2(1)(c); "
                    "SEBI Consultation Paper on SME Framework (Nov 2024), "
                    "Section 3.1 — Enhanced Scrutiny of Working Capital Requirements"
                ),
                related_data={
                    "working_capital_amount_lakhs": str(item.amount),
                    "avg_annual_revenue_increase_lakhs": str(baseline),
                    "multiplier": f"{multiplier:.1f}",
                    "threshold_multiplier": str(WORKING_CAPITAL_GROWTH_MULTIPLIER),
                    "revenue_earliest_lakhs": str(revenues[0]),
                    "revenue_latest_lakhs": str(revenues[-1]),
                    "justification_length": len((item.justification or "").strip()),
                },
            ))

    return flags


def run_objects_rules(objects_of_issue, use_of_proceeds, rpts, shareholders,
                      financial_summaries):
    """Run all Objects of the Issue rules and return combined flags."""
    flags = []
    flags.extend(check_debt_repayment_to_promoter(use_of_proceeds, rpts, shareholders))
    flags.extend(check_gcp_threshold(objects_of_issue, use_of_proceeds))
    flags.extend(check_working_capital_disproportionate(
        use_of_proceeds, financial_summaries
    ))
    return flags
