"""
Trinity Validation Engine — Cross-Section Consistency Rules

Rules that compare data across multiple DRHP sections to flag
inconsistencies or missing cross-references.

Based on SEBI ICDR Regulations 2018, Chapter IX, and SEBI Consultation
Paper on SME Segment Framework (Nov 2024).
"""

from decimal import Decimal

from .flag import FlagResult


def check_promoter_in_litigation(shareholders, litigations):
    """
    Rule: promoter_in_litigation

    Flag if a person's name appears in ShareholderEntry as "promoter" (or
    "promoter_group") but also appears in LitigationEntry — to prompt the
    user to confirm whether that litigation involves a promoter (which has
    specific mandatory disclosure requirements under ICDR).

    Matching is done case-insensitively on substrings: the promoter name
    is checked against both `party_involved` and `court_or_authority` fields
    of each litigation entry.

    Input:
        - shareholders: list of ShareholderEntry objects
        - litigations: list of LitigationEntry objects
    Output: List[FlagResult]
    """
    flags = []

    if not shareholders or not litigations:
        return flags

    # Collect promoter names
    promoter_names = []
    for sh in shareholders:
        if sh.category in ("promoter", "promoter_group"):
            promoter_names.append(sh.shareholder_name.strip())

    if not promoter_names:
        return flags

    for promoter_name in promoter_names:
        name_lower = promoter_name.lower()

        matching_litigations = []
        for lit in litigations:
            party_lower = (lit.party_involved or "").lower()
            # Check if promoter name appears in the party_involved field
            if name_lower in party_lower:
                matching_litigations.append({
                    "case_type": lit.case_type,
                    "party_involved": lit.party_involved,
                    "court_or_authority": lit.court_or_authority,
                    "status": lit.status[:100],
                    "amount_involved_lakhs": str(lit.amount_involved) if lit.amount_involved else None,
                })

        if matching_litigations:
            flags.append(FlagResult(
                rule_id="promoter_in_litigation",
                severity="warning",
                section="cross_section",
                field_reference=(
                    f"shareholders.shareholder_name={promoter_name}; "
                    f"litigations.party_involved"
                ),
                message=(
                    f"Promoter '{promoter_name}' appears to be involved in "
                    f"{len(matching_litigations)} litigation/regulatory "
                    f"proceeding(s). Litigation involving promoters has mandatory "
                    f"disclosure requirements under ICDR (criminal cases against "
                    f"promoters must be disclosed regardless of materiality). "
                    f"Please confirm and ensure proper cross-referencing."
                ),
                regulation_citation=(
                    "SEBI ICDR 2018, Schedule VI, Part A, Clause 17; "
                    "Clause 17(a) — Mandatory disclosure of all criminal "
                    "proceedings against promoters and directors"
                ),
                related_data={
                    "promoter_name": promoter_name,
                    "matching_litigation_count": len(matching_litigations),
                    "matching_litigations": matching_litigations,
                },
            ))

    return flags


def check_shareholding_percentage_sanity(shareholders):
    """
    Rule: shareholding_percentage_sanity

    Flag if promoter shareholding percentages across all ShareholderEntry
    records do not sum to a plausible total. This is a sanity check, not
    a hard 100% rule, since post-issue dilution applies.

    Checks:
      - Total of all holdings should be close to 100% (between 95% and 105%
        to allow for rounding). If outside this range, flag for review.
      - Promoter + promoter group combined should typically be > 20%
        (minimum promoter contribution under ICDR Reg 236).

    Input:
        - shareholders: list of ShareholderEntry objects
    Output: List[FlagResult]
    """
    flags = []

    if not shareholders:
        return flags

    total_pct = Decimal("0")
    promoter_pct = Decimal("0")

    for sh in shareholders:
        pct = sh.percentage_holding or Decimal("0")
        total_pct += pct
        if sh.category in ("promoter", "promoter_group"):
            promoter_pct += pct

    # Check 1: Total should be approximately 100%
    if total_pct < Decimal("95") or total_pct > Decimal("105"):
        flags.append(FlagResult(
            rule_id="shareholding_total_sanity",
            severity="warning",
            section="capital_structure",
            field_reference="shareholders.percentage_holding",
            message=(
                f"Total shareholding across all entries sums to {total_pct:.2f}%, "
                f"which is outside the expected range of 95–105%. This may indicate "
                f"missing shareholders or data entry errors. Please verify that all "
                f"shareholders are accounted for."
            ),
            regulation_citation=(
                "SEBI ICDR 2018, Schedule VI, Part A, Clauses 4 & 5 — "
                "Capital Structure disclosure must account for all issued shares"
            ),
            related_data={
                "total_percentage": str(total_pct),
                "expected_range": "95–105",
                "shareholder_count": len(shareholders),
            },
        ))

    # Check 2: Promoter holding should be >= 20% (minimum contribution)
    if promoter_pct < Decimal("20") and len(shareholders) > 0:
        flags.append(FlagResult(
            rule_id="promoter_minimum_contribution",
            severity="warning",
            section="capital_structure",
            field_reference="shareholders.percentage_holding (promoter + promoter_group)",
            message=(
                f"Combined promoter and promoter group holding is {promoter_pct:.2f}%, "
                f"which is below the 20% minimum promoter contribution required under "
                f"ICDR Regulation 236. Note: this refers to post-issue holding; if this "
                f"is pre-issue data, the actual post-issue percentage may differ."
            ),
            regulation_citation=(
                "SEBI ICDR 2018, Regulation 236 — Minimum Promoters' Contribution "
                "(20% of post-issue capital, locked in for 3 years)"
            ),
            related_data={
                "promoter_percentage": str(promoter_pct),
                "minimum_required": "20",
                "total_percentage": str(total_pct),
            },
        ))

    return flags


def run_cross_section_rules(shareholders, litigations):
    """Run all cross-section consistency rules and return combined flags."""
    flags = []
    flags.extend(check_promoter_in_litigation(shareholders, litigations))
    flags.extend(check_shareholding_percentage_sanity(shareholders))
    return flags
