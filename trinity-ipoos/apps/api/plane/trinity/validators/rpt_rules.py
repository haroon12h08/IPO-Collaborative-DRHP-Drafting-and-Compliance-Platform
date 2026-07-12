"""
Trinity Validation Engine — Related Party Transaction Rules

Rules based on SEBI ICDR Regulations 2018, Chapter IX, Schedule VI, Part A,
Clause 14 and SEBI Consultation Paper on SME Segment Framework (Nov 2024).

All amounts in this module are in ₹ Lakhs (matching the database storage unit).
₹10 crore = ₹1,000 lakhs.
"""

from collections import defaultdict
from decimal import Decimal

from .flag import FlagResult

# Threshold constants (in Lakhs)
SINGLE_PARTY_THRESHOLD_LAKHS = Decimal("1000")  # ₹10 crore
REVENUE_PERCENTAGE_THRESHOLD = Decimal("0.10")   # 10%


def check_single_party_threshold(rpts):
    """
    Rule: rpt_single_party_threshold

    Flag if the sum of RPTs with any single related party in a single
    financial year exceeds ₹10 crore (₹1,000 lakhs).

    Input:  QuerySet or list of RelatedPartyTransaction objects.
    Output: List[FlagResult]
    """
    flags = []

    # Aggregate: (related_party_name, financial_year) → total amount
    party_fy_totals = defaultdict(Decimal)
    for rpt in rpts:
        key = (rpt.related_party_name, rpt.financial_year)
        party_fy_totals[key] += rpt.amount

    for (party_name, fy), total in party_fy_totals.items():
        if total > SINGLE_PARTY_THRESHOLD_LAKHS:
            flags.append(FlagResult(
                rule_id="rpt_single_party_threshold",
                severity="warning",
                section="related_party_transactions",
                field_reference=f"related_party_name={party_name}, financial_year={fy}",
                message=(
                    f"Aggregate RPT amount with '{party_name}' in FY {fy} is "
                    f"₹{total:,.2f} lakhs (₹{total / 100:,.2f} crore), which exceeds "
                    f"the ₹10 crore threshold. This transaction requires enhanced "
                    f"disclosure and board/audit committee approval under SEBI norms."
                ),
                regulation_citation=(
                    "SEBI ICDR 2018, Schedule VI, Part A, Clause 14; "
                    "SEBI Consultation Paper on SME Framework (Nov 2024), "
                    "Section 3.2 — Material RPT Thresholds"
                ),
                related_data={
                    "related_party_name": party_name,
                    "financial_year": fy,
                    "total_amount_lakhs": str(total),
                    "threshold_lakhs": str(SINGLE_PARTY_THRESHOLD_LAKHS),
                    "total_amount_crore": str(total / 100),
                    "threshold_crore": "10",
                },
            ))

    return flags


def check_rpt_revenue_percentage(rpts, financial_summaries):
    """
    Rule: rpt_revenue_percentage

    Flag if total RPTs across all related parties in a financial year
    exceed 10% of that year's reported revenue.

    Input:  - rpts: QuerySet/list of RelatedPartyTransaction objects.
            - financial_summaries: QuerySet/list of FinancialYearSummary objects.
    Output: List[FlagResult]
    """
    flags = []

    # Build revenue lookup: financial_year → revenue
    revenue_by_fy = {}
    for fs in financial_summaries:
        revenue_by_fy[fs.financial_year] = fs.revenue

    # Aggregate total RPTs per financial year
    fy_rpt_totals = defaultdict(Decimal)
    for rpt in rpts:
        fy_rpt_totals[rpt.financial_year] += rpt.amount

    for fy, total_rpt in fy_rpt_totals.items():
        revenue = revenue_by_fy.get(fy)
        if revenue is None or revenue <= 0:
            continue  # No revenue data for this FY — can't compute ratio

        percentage = (total_rpt / revenue) * 100
        if total_rpt > revenue * REVENUE_PERCENTAGE_THRESHOLD:
            flags.append(FlagResult(
                rule_id="rpt_revenue_percentage",
                severity="warning",
                section="related_party_transactions",
                field_reference=f"financial_year={fy}",
                message=(
                    f"Total RPTs in FY {fy} amount to ₹{total_rpt:,.2f} lakhs, "
                    f"which is {percentage:.1f}% of reported revenue "
                    f"(₹{revenue:,.2f} lakhs). This exceeds the 10% threshold "
                    f"and requires enhanced scrutiny under SEBI norms."
                ),
                regulation_citation=(
                    "SEBI ICDR 2018, Schedule VI, Part A, Clause 14(d); "
                    "SEBI Consultation Paper on SME Framework (Nov 2024), "
                    "Section 3.2 — RPT Materiality Relative to Revenue"
                ),
                related_data={
                    "financial_year": fy,
                    "total_rpt_lakhs": str(total_rpt),
                    "revenue_lakhs": str(revenue),
                    "percentage_of_revenue": f"{percentage:.2f}",
                    "threshold_percentage": "10",
                },
            ))

    return flags


def run_rpt_rules(rpts, financial_summaries):
    """Run all RPT rules and return combined flags."""
    flags = []
    flags.extend(check_single_party_threshold(rpts))
    flags.extend(check_rpt_revenue_percentage(rpts, financial_summaries))
    return flags
