"""
Trinity Validation Engine — Unit Tests

Tests every rule function with deterministic inputs.
Each test verifies exact flag output for a known input scenario.

Run via:  docker exec plane-api-1 python manage.py test plane.trinity.tests.test_validators --settings=plane.settings.local
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from unittest import TestCase

from plane.trinity.validators.flag import FlagResult
from plane.trinity.validators.rpt_rules import (
    check_single_party_threshold,
    check_rpt_revenue_percentage,
)
from plane.trinity.validators.objects_rules import (
    check_debt_repayment_to_promoter,
    check_gcp_threshold,
    check_working_capital_disproportionate,
)
from plane.trinity.validators.cross_section_rules import (
    check_promoter_in_litigation,
    check_shareholding_percentage_sanity,
)
from plane.trinity.validators.completeness_rules import (
    _is_field_empty,
    run_completeness_rules,
    check_objects_of_issue_completeness,
    check_collection_completeness,
)
from .test_drafting import TestDraftingLayer


# ---------------------------------------------------------------------------
# Stub objects that mimic Django model instances for pure-logic testing
# ---------------------------------------------------------------------------


@dataclass
class StubRPT:
    related_party_name: str
    relationship_type: str
    transaction_type: str
    amount: Decimal
    financial_year: str
    is_arms_length: bool = True
    id: str = None


@dataclass
class StubFinancialSummary:
    financial_year: str
    revenue: Decimal
    ebitda: Decimal
    pat: Decimal
    net_worth: Decimal
    id: str = None


@dataclass
class StubUseOfProceeds:
    category: str
    amount: Decimal
    justification: str = ""
    repayment_counterparty_id: str = None
    id: str = None


@dataclass
class StubObjectsOfIssue:
    fresh_issue_amount: Decimal = None
    id: str = None


@dataclass
class StubShareholder:
    shareholder_name: str
    category: str  # "promoter", "promoter_group", "public"
    number_of_shares: int = 0
    percentage_holding: Decimal = Decimal("0")
    date_of_acquisition: date = None
    acquisition_price_per_share: Decimal = Decimal("0")
    id: str = None


@dataclass
class StubLitigation:
    case_type: str
    party_involved: str
    court_or_authority: str
    status: str
    amount_involved: Decimal = None
    id: str = None


# ===========================================================================
# RPT Rules
# ===========================================================================


class TestRPTSinglePartyThreshold(TestCase):
    """Rule: rpt_single_party_threshold — flag if > ₹10 crore (1000 lakhs)."""

    def test_no_flag_below_threshold(self):
        rpts = [
            StubRPT("ABC Corp", "promoter", "sale", Decimal("500"), "2023-2024"),
            StubRPT("ABC Corp", "promoter", "service", Decimal("400"), "2023-2024"),
        ]
        flags = check_single_party_threshold(rpts)
        self.assertEqual(len(flags), 0)

    def test_flag_above_threshold(self):
        rpts = [
            StubRPT("ABC Corp", "promoter", "sale", Decimal("600"), "2023-2024"),
            StubRPT("ABC Corp", "promoter", "service", Decimal("500"), "2023-2024"),
        ]
        flags = check_single_party_threshold(rpts)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].rule_id, "rpt_single_party_threshold")
        self.assertEqual(flags[0].severity, "warning")
        self.assertIn("1,100.00", flags[0].message)

    def test_exact_threshold_no_flag(self):
        rpts = [
            StubRPT("XYZ Ltd", "director", "sale", Decimal("1000"), "2023-2024"),
        ]
        flags = check_single_party_threshold(rpts)
        self.assertEqual(len(flags), 0)

    def test_multiple_parties_only_exceeding_flagged(self):
        rpts = [
            StubRPT("ABC Corp", "promoter", "sale", Decimal("1200"), "2023-2024"),
            StubRPT("DEF Ltd", "director", "purchase", Decimal("500"), "2023-2024"),
        ]
        flags = check_single_party_threshold(rpts)
        self.assertEqual(len(flags), 1)
        self.assertIn("ABC Corp", flags[0].message)

    def test_same_party_different_fy_separate(self):
        rpts = [
            StubRPT("ABC Corp", "promoter", "sale", Decimal("800"), "2022-2023"),
            StubRPT("ABC Corp", "promoter", "sale", Decimal("800"), "2023-2024"),
        ]
        flags = check_single_party_threshold(rpts)
        self.assertEqual(len(flags), 0)  # Neither FY exceeds on its own


class TestRPTRevenuePercentage(TestCase):
    """Rule: rpt_revenue_percentage — flag if total RPTs > 10% of revenue."""

    def test_no_flag_below_10_percent(self):
        rpts = [StubRPT("A", "promoter", "sale", Decimal("50"), "2023-2024")]
        financials = [StubFinancialSummary("2023-2024", Decimal("1000"), Decimal("100"), Decimal("50"), Decimal("200"))]
        flags = check_rpt_revenue_percentage(rpts, financials)
        self.assertEqual(len(flags), 0)

    def test_flag_above_10_percent(self):
        rpts = [
            StubRPT("A", "promoter", "sale", Decimal("80"), "2023-2024"),
            StubRPT("B", "director", "purchase", Decimal("30"), "2023-2024"),
        ]
        financials = [StubFinancialSummary("2023-2024", Decimal("1000"), Decimal("100"), Decimal("50"), Decimal("200"))]
        flags = check_rpt_revenue_percentage(rpts, financials)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].rule_id, "rpt_revenue_percentage")
        self.assertIn("11.0%", flags[0].message)

    def test_no_financial_data_no_flag(self):
        rpts = [StubRPT("A", "promoter", "sale", Decimal("999"), "2023-2024")]
        flags = check_rpt_revenue_percentage(rpts, [])
        self.assertEqual(len(flags), 0)


# ===========================================================================
# Objects of Issue Rules
# ===========================================================================


class TestDebtRepaymentToPromoter(TestCase):
    """Rule: debt_repayment_to_promoter — blocking if structured, warning if legacy string match."""

    def test_no_flag_when_no_debt_repayment(self):
        uop = [StubUseOfProceeds("capex", Decimal("500"), "For machinery")]
        rpts = [StubRPT("John Doe", "promoter", "sale", Decimal("50"), "2023-2024", id="rpt-1")]
        flags = check_debt_repayment_to_promoter(uop, rpts, [])
        self.assertEqual(len(flags), 0)

    def test_flag_when_promoter_name_in_justification(self):
        uop = [StubUseOfProceeds("debt_repayment", Decimal("300"), "Repayment of loan from John Doe")]
        rpts = [StubRPT("John Doe", "promoter", "loan", Decimal("300"), "2023-2024", id="rpt-1")]
        flags = check_debt_repayment_to_promoter(uop, rpts, [])
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "warning")  # Downgraded to warning for legacy fallback
        self.assertEqual(flags[0].rule_id, "debt_repayment_to_promoter")

    def test_flag_uses_shareholder_names_too(self):
        uop = [StubUseOfProceeds("debt_repayment", Decimal("300"), "Repay to Jane Smith")]
        shareholders = [StubShareholder("Jane Smith", "promoter", id="sh-1")]
        flags = check_debt_repayment_to_promoter(uop, [], shareholders)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "warning")  # Downgraded to warning for legacy fallback

    def test_no_flag_when_non_promoter_name(self):
        uop = [StubUseOfProceeds("debt_repayment", Decimal("300"), "Bank of India term loan repayment")]
        rpts = [StubRPT("John Doe", "promoter", "sale", Decimal("50"), "2023-2024", id="rpt-1")]
        flags = check_debt_repayment_to_promoter(uop, rpts, [])
        self.assertEqual(len(flags), 0)

    def test_case_insensitive_matching(self):
        uop = [StubUseOfProceeds("debt_repayment", Decimal("300"), "repayment to JOHN DOE")]
        rpts = [StubRPT("john doe", "promoter", "loan", Decimal("300"), "2023-2024", id="rpt-1")]
        flags = check_debt_repayment_to_promoter(uop, rpts, [])
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "warning")

    def test_structured_match_rpt_blocking(self):
        uop = [StubUseOfProceeds("debt_repayment", Decimal("300"), "Repayment", repayment_counterparty_id="rpt-uuid-1")]
        rpts = [StubRPT("John Doe", "promoter", "loan", Decimal("300"), "2023-2024", id="rpt-uuid-1")]
        flags = check_debt_repayment_to_promoter(uop, rpts, [])
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "blocking")
        self.assertEqual(flags[0].rule_id, "debt_repayment_to_promoter")

    def test_structured_match_shareholder_blocking(self):
        uop = [StubUseOfProceeds("debt_repayment", Decimal("300"), "Repay", repayment_counterparty_id="sh-uuid-1")]
        shareholders = [StubShareholder("Jane Smith", "promoter", id="sh-uuid-1")]
        flags = check_debt_repayment_to_promoter(uop, [], shareholders)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "blocking")

    def test_structured_match_non_promoter_no_flag(self):
        uop = [StubUseOfProceeds("debt_repayment", Decimal("300"), "Repay bank", repayment_counterparty_id="sh-uuid-2")]
        shareholders = [StubShareholder("Public Shareholder", "public", id="sh-uuid-2")]
        flags = check_debt_repayment_to_promoter(uop, [], shareholders)
        self.assertEqual(len(flags), 0)


class TestGCPThreshold(TestCase):
    """Rule: gcp_threshold — flag if GCP > min(10% of issue, ₹10 crore)."""

    def test_no_flag_below_threshold(self):
        ooi = StubObjectsOfIssue(Decimal("5000"))
        uop = [StubUseOfProceeds("general_corporate_purposes", Decimal("400"))]
        flags = check_gcp_threshold(ooi, uop)
        self.assertEqual(len(flags), 0)

    def test_flag_exceeds_10_percent(self):
        ooi = StubObjectsOfIssue(Decimal("5000"))
        uop = [StubUseOfProceeds("general_corporate_purposes", Decimal("600"))]
        flags = check_gcp_threshold(ooi, uop)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "blocking")

    def test_flag_exceeds_10_crore_absolute_cap(self):
        # Issue is ₹200 crore (20000 lakhs), so 10% = 2000 lakhs > 1000 lakhs cap
        ooi = StubObjectsOfIssue(Decimal("20000"))
        uop = [StubUseOfProceeds("general_corporate_purposes", Decimal("1200"))]
        flags = check_gcp_threshold(ooi, uop)
        self.assertEqual(len(flags), 1)
        self.assertIn("₹10 crore", flags[0].message)

    def test_no_flag_when_no_objects(self):
        flags = check_gcp_threshold(None, [])
        self.assertEqual(len(flags), 0)


class TestWorkingCapitalDisproportionate(TestCase):
    """Rule: working_capital_disproportionate — flag if WC > 3× avg revenue growth."""

    def test_no_flag_with_justification(self):
        uop = [StubUseOfProceeds("working_capital", Decimal("500"), "Detailed rationale for WC requirement goes here")]
        financials = [
            StubFinancialSummary("2021-2022", Decimal("500"), Decimal("50"), Decimal("25"), Decimal("100")),
            StubFinancialSummary("2022-2023", Decimal("600"), Decimal("60"), Decimal("30"), Decimal("120")),
            StubFinancialSummary("2023-2024", Decimal("700"), Decimal("70"), Decimal("35"), Decimal("140")),
        ]
        flags = check_working_capital_disproportionate(uop, financials)
        self.assertEqual(len(flags), 0)  # Has justification

    def test_flag_disproportionate_without_justification(self):
        uop = [StubUseOfProceeds("working_capital", Decimal("500"), "")]
        financials = [
            StubFinancialSummary("2021-2022", Decimal("500"), Decimal("50"), Decimal("25"), Decimal("100")),
            StubFinancialSummary("2022-2023", Decimal("550"), Decimal("55"), Decimal("28"), Decimal("110")),
            StubFinancialSummary("2023-2024", Decimal("600"), Decimal("60"), Decimal("30"), Decimal("120")),
        ]
        # Avg annual increase = (600-500)/2 = 50. WC 500 > 50*3=150. Flag!
        flags = check_working_capital_disproportionate(uop, financials)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].rule_id, "working_capital_disproportionate")

    def test_no_flag_proportionate_without_justification(self):
        uop = [StubUseOfProceeds("working_capital", Decimal("100"), "")]
        financials = [
            StubFinancialSummary("2021-2022", Decimal("500"), Decimal("50"), Decimal("25"), Decimal("100")),
            StubFinancialSummary("2022-2023", Decimal("700"), Decimal("70"), Decimal("35"), Decimal("140")),
            StubFinancialSummary("2023-2024", Decimal("900"), Decimal("90"), Decimal("45"), Decimal("180")),
        ]
        # Avg annual increase = (900-500)/2 = 200. WC 100 < 200*3=600. No flag.
        flags = check_working_capital_disproportionate(uop, financials)
        self.assertEqual(len(flags), 0)


# ===========================================================================
# Cross-Section Rules
# ===========================================================================


class TestPromoterInLitigation(TestCase):
    """Rule: promoter_in_litigation — flag if promoter name appears in litigation."""

    def test_no_flag_when_no_match(self):
        shareholders = [StubShareholder("John Doe", "promoter")]
        litigations = [StubLitigation("civil", "XYZ Corp vs ABC Ltd", "High Court", "Pending")]
        flags = check_promoter_in_litigation(shareholders, litigations)
        self.assertEqual(len(flags), 0)

    def test_flag_when_promoter_in_party_involved(self):
        shareholders = [StubShareholder("John Doe", "promoter")]
        litigations = [StubLitigation("criminal", "State vs John Doe", "Sessions Court", "Pending")]
        flags = check_promoter_in_litigation(shareholders, litigations)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].rule_id, "promoter_in_litigation")

    def test_case_insensitive_match(self):
        shareholders = [StubShareholder("JOHN DOE", "promoter")]
        litigations = [StubLitigation("criminal", "State vs john doe", "Court", "Pending")]
        flags = check_promoter_in_litigation(shareholders, litigations)
        self.assertEqual(len(flags), 1)

    def test_no_flag_for_public_shareholders(self):
        shareholders = [StubShareholder("John Doe", "public")]
        litigations = [StubLitigation("criminal", "State vs John Doe", "Court", "Pending")]
        flags = check_promoter_in_litigation(shareholders, litigations)
        self.assertEqual(len(flags), 0)


class TestShareholdingSanity(TestCase):
    """Rule: shareholding_percentage_sanity — flag if totals are implausible."""

    def test_no_flag_for_valid_totals(self):
        shareholders = [
            StubShareholder("John", "promoter", percentage_holding=Decimal("55")),
            StubShareholder("Public", "public", percentage_holding=Decimal("45")),
        ]
        flags = check_shareholding_percentage_sanity(shareholders)
        self.assertEqual(len(flags), 0)

    def test_flag_when_total_too_low(self):
        shareholders = [
            StubShareholder("John", "promoter", percentage_holding=Decimal("40")),
        ]
        flags = check_shareholding_percentage_sanity(shareholders)
        total_sanity = [f for f in flags if f.rule_id == "shareholding_total_sanity"]
        self.assertEqual(len(total_sanity), 1)

    def test_flag_when_promoter_below_20_percent(self):
        shareholders = [
            StubShareholder("John", "promoter", percentage_holding=Decimal("15")),
            StubShareholder("Public", "public", percentage_holding=Decimal("85")),
        ]
        flags = check_shareholding_percentage_sanity(shareholders)
        min_contrib = [f for f in flags if f.rule_id == "promoter_minimum_contribution"]
        self.assertEqual(len(min_contrib), 1)

    def test_no_flag_for_empty_list(self):
        flags = check_shareholding_percentage_sanity([])
        self.assertEqual(len(flags), 0)


# ===========================================================================
# Completeness Helpers
# ===========================================================================


class TestIsFieldEmpty(TestCase):
    """Unit tests for the _is_field_empty helper."""

    def test_none_is_empty(self):
        self.assertTrue(_is_field_empty(None))

    def test_empty_string_is_empty(self):
        self.assertTrue(_is_field_empty(""))
        self.assertTrue(_is_field_empty("   "))

    def test_zero_is_not_empty(self):
        self.assertFalse(_is_field_empty(0))
        self.assertFalse(_is_field_empty(Decimal("0")))

    def test_value_is_not_empty(self):
        self.assertFalse(_is_field_empty("hello"))
        self.assertFalse(_is_field_empty(42))
        self.assertFalse(_is_field_empty(Decimal("100.50")))


class TestCompletenessRules(TestCase):
    """Unit tests for the completeness validation rules."""

    def test_objects_of_issue_missing(self):
        # objects_of_issue is None
        flags = run_completeness_rules(None, [], [], [], [], [])
        missing_section = [f for f in flags if f.rule_id == "completeness_section_missing"]
        self.assertEqual(len(missing_section), 1)
        self.assertEqual(missing_section[0].severity, "blocking")
        self.assertEqual(missing_section[0].section, "objects_of_issue")

    def test_objects_of_issue_no_line_items(self):
        # Objects of issue exists, but no line items
        ooi = StubObjectsOfIssue(fresh_issue_amount=Decimal("1000"))
        flags = run_completeness_rules(ooi, [], [], [], [], [])
        no_line_items = [f for f in flags if f.rule_id == "completeness_no_line_items"]
        self.assertEqual(len(no_line_items), 1)
        self.assertEqual(no_line_items[0].severity, "blocking")

    def test_objects_of_issue_missing_required_fields(self):
        # ooi has fresh_issue_amount as None (required field)
        ooi = StubObjectsOfIssue(fresh_issue_amount=None)
        flags = run_completeness_rules(ooi, [StubUseOfProceeds("capex", Decimal("1000"), "Justification")], [], [], [], [])
        req_field = [f for f in flags if f.rule_id == "completeness_required_field"]
        self.assertEqual(len(req_field), 1)
        self.assertEqual(req_field[0].severity, "blocking")
        self.assertIn("fresh_issue_amount", req_field[0].field_reference)

    def test_collection_section_empty(self):
        # RPTs list is empty
        ooi = StubObjectsOfIssue(fresh_issue_amount=Decimal("1000"))
        uop = [StubUseOfProceeds("capex", Decimal("1000"), "Justification")]
        flags = run_completeness_rules(ooi, uop, [], [], [], [])
        empty_section = [f for f in flags if f.rule_id == "completeness_section_empty"]
        # Expected empty sections: related_party_transactions, capital_structure, financial_summary.
        # (Litigation allows empty, so it's not a warning/info flag or is handled)
        sections = {f.section for f in empty_section}
        self.assertIn("related_party_transactions", sections)
        self.assertIn("capital_structure", sections)
        self.assertIn("financial_summary", sections)

    def test_insufficient_records_financials(self):
        # financials has only 1 record (min expected is 3)
        ooi = StubObjectsOfIssue(fresh_issue_amount=Decimal("1000"))
        uop = [StubUseOfProceeds("capex", Decimal("1000"), "Justification")]
        financials = [StubFinancialSummary("2023-2024", Decimal("100"), Decimal("10"), Decimal("5"), Decimal("50"))]
        flags = run_completeness_rules(ooi, uop, [], [], [], financials)
        insufficient = [f for f in flags if f.rule_id == "completeness_insufficient_records"]
        self.assertEqual(len(insufficient), 1)
        self.assertEqual(insufficient[0].section, "financial_summary")
        self.assertEqual(insufficient[0].severity, "warning")
