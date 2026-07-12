"""
Trinity IPO Preparation Tool — Data Models

All models extend Plane's BaseModel (UUID primary key, audit fields, soft delete)
and link to a Workspace via foreign key. No modifications to Plane's existing
workspace, auth, or permission models.

Each model corresponds to one of the 5 DRHP disclosure sections required by
SEBI ICDR Regulations 2018, Chapter IX, Schedule VI.
"""

from django.conf import settings
from django.db import models

from plane.db.models.base import BaseModel


# ---------------------------------------------------------------------------
# IPO Workspace — ties a Plane workspace to an IPO preparation context
# ---------------------------------------------------------------------------


class IPOWorkspace(BaseModel):
    """
    Represents an IPO preparation workspace linked to a Plane workspace.
    One Plane workspace can have at most one IPO context.
    """

    workspace = models.OneToOneField(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="ipo_workspace",
    )
    company_name = models.CharField(max_length=255, verbose_name="Company Legal Name")
    cin = models.CharField(
        max_length=21,
        blank=True,
        null=True,
        verbose_name="Corporate Identity Number (CIN)",
    )
    exchange_target = models.CharField(
        max_length=50,
        choices=[
            ("nse_emerge", "NSE Emerge (SME)"),
            ("bse_sme", "BSE SME"),
        ],
        default="nse_emerge",
        verbose_name="Target Exchange",
    )
    status = models.CharField(
        max_length=30,
        choices=[
            ("draft", "Draft — Data Entry in Progress"),
            ("review", "Under Review"),
            ("submitted", "Submitted to Merchant Banker"),
        ],
        default="draft",
    )

    class Meta:
        verbose_name = "IPO Workspace"
        verbose_name_plural = "IPO Workspaces"
        db_table = "trinity_ipo_workspaces"
        ordering = ("-created_at",)

    def __str__(self):
        return f"IPO: {self.company_name} ({self.workspace.slug})"


# ---------------------------------------------------------------------------
# Section 1 — Objects of the Issue
# ---------------------------------------------------------------------------


class ObjectsOfIssue(BaseModel):
    """
    Header record for the Objects of the Issue section.
    ICDR Reference: Schedule VI, Part A, Clause 2(1)
    """

    ipo_workspace = models.OneToOneField(
        IPOWorkspace,
        on_delete=models.CASCADE,
        related_name="objects_of_issue",
    )
    fresh_issue_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Fresh Issue Amount (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 2(1)(a)",
    )

    class Meta:
        verbose_name = "Objects of the Issue"
        verbose_name_plural = "Objects of the Issue"
        db_table = "trinity_objects_of_issue"

    def __str__(self):
        return f"Objects of Issue — {self.ipo_workspace.company_name}"


class UseOfProceeds(BaseModel):
    """
    Individual line item within Objects of the Issue.
    ICDR Reference: Schedule VI, Part A, Clause 2(1)(b)
    """

    CATEGORY_CHOICES = [
        ("capex", "Capital Expenditure"),
        ("working_capital", "Working Capital"),
        ("general_corporate_purposes", "General Corporate Purposes"),
        ("debt_repayment", "Debt Repayment"),
        ("other", "Other"),
    ]

    objects_of_issue = models.ForeignKey(
        ObjectsOfIssue,
        on_delete=models.CASCADE,
        related_name="use_of_proceeds",
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name="Use of Proceeds Category",
        help_text="Schedule VI, Part A, Clause 2(1)(b)",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Amount (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 2(1)(a)",
    )
    justification = models.TextField(
        verbose_name="Justification / Rationale",
        help_text="Schedule VI, Part A, Clause 2(1)(c)",
    )
    repayment_counterparty_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="Repayment Counterparty ID",
        help_text="Reference to existing ShareholderEntry or RelatedPartyTransaction party UUID",
    )
    sort_order = models.FloatField(default=65535)

    class Meta:
        verbose_name = "Use of Proceeds"
        verbose_name_plural = "Use of Proceeds"
        db_table = "trinity_use_of_proceeds"
        ordering = ("sort_order", "created_at")

    def __str__(self):
        return f"{self.get_category_display()} — ₹{self.amount}L"


# ---------------------------------------------------------------------------
# Section 2 — Related Party Transactions
# ---------------------------------------------------------------------------


class RelatedPartyTransaction(BaseModel):
    """
    Individual Related Party Transaction entry.
    ICDR Reference: Schedule VI, Part A, Clause 14
    """

    RELATIONSHIP_CHOICES = [
        ("promoter", "Promoter"),
        ("promoter_group", "Promoter Group Entity"),
        ("director", "Director"),
        ("key_management_personnel", "Key Management Personnel"),
        ("subsidiary", "Subsidiary Company"),
        ("associate", "Associate Company"),
        ("joint_venture", "Joint Venture"),
        ("relative_of_director", "Relative of Director/KMP"),
        ("entity_with_common_control", "Entity under Common Control"),
        ("other", "Other Related Party"),
    ]

    ipo_workspace = models.ForeignKey(
        IPOWorkspace,
        on_delete=models.CASCADE,
        related_name="related_party_transactions",
    )
    related_party_name = models.CharField(
        max_length=255,
        verbose_name="Related Party Name",
        help_text="Schedule VI, Part A, Clause 14(a)",
    )
    relationship_type = models.CharField(
        max_length=50,
        choices=RELATIONSHIP_CHOICES,
        verbose_name="Relationship Type",
        help_text="Schedule VI, Part A, Clause 14(b)",
    )
    transaction_type = models.CharField(
        max_length=255,
        verbose_name="Transaction Type",
        help_text="Schedule VI, Part A, Clause 14(c)",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Transaction Amount (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 14(d)",
    )
    financial_year = models.CharField(
        max_length=9,
        verbose_name="Financial Year",
        help_text="Format: YYYY-YYYY (e.g., 2023-2024)",
    )
    is_arms_length = models.BooleanField(
        default=True,
        verbose_name="At Arm's Length?",
        help_text="Schedule VI, Part A, Clause 14(e)",
    )

    class Meta:
        verbose_name = "Related Party Transaction"
        verbose_name_plural = "Related Party Transactions"
        db_table = "trinity_related_party_transactions"
        ordering = ("-financial_year", "related_party_name")

    def __str__(self):
        return f"RPT: {self.related_party_name} — {self.financial_year}"


# ---------------------------------------------------------------------------
# Section 3 — Capital Structure / Promoter Shareholding
# ---------------------------------------------------------------------------


class ShareholderEntry(BaseModel):
    """
    Individual shareholding entry.
    ICDR Reference: Schedule VI, Part A, Clauses 4 & 5
    """

    CATEGORY_CHOICES = [
        ("promoter", "Promoter"),
        ("promoter_group", "Promoter Group"),
        ("public", "Public Shareholder"),
    ]

    ipo_workspace = models.ForeignKey(
        IPOWorkspace,
        on_delete=models.CASCADE,
        related_name="shareholders",
    )
    shareholder_name = models.CharField(
        max_length=255,
        verbose_name="Shareholder Name",
        help_text="Schedule VI, Part A, Clause 5(a)",
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name="Shareholder Category",
        help_text="Schedule VI, Part A, Clause 5(b)",
    )
    number_of_shares = models.PositiveBigIntegerField(
        verbose_name="Number of Equity Shares",
        help_text="Schedule VI, Part A, Clause 5(c)",
    )
    percentage_holding = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Percentage Holding (%)",
        help_text="Schedule VI, Part A, Clause 5(c)",
    )
    date_of_acquisition = models.DateField(
        verbose_name="Date of Acquisition / Allotment",
        help_text="Schedule VI, Part A, Clause 5(d)",
    )
    acquisition_price_per_share = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Acquisition Price per Share (₹)",
        help_text="Schedule VI, Part A, Clause 5(d)",
    )

    class Meta:
        verbose_name = "Shareholder Entry"
        verbose_name_plural = "Shareholder Entries"
        db_table = "trinity_shareholder_entries"
        ordering = ("category", "shareholder_name")

    def __str__(self):
        return f"{self.shareholder_name} — {self.percentage_holding}%"


# ---------------------------------------------------------------------------
# Section 4 — Litigation & Regulatory Actions
# ---------------------------------------------------------------------------


class LitigationEntry(BaseModel):
    """
    Individual litigation or regulatory action entry.
    ICDR Reference: Schedule VI, Part A, Clause 17
    """

    CASE_TYPE_CHOICES = [
        ("criminal", "Criminal Proceedings"),
        ("civil", "Civil Litigation"),
        ("regulatory", "Regulatory Actions"),
        ("tax", "Tax Proceedings"),
    ]

    ipo_workspace = models.ForeignKey(
        IPOWorkspace,
        on_delete=models.CASCADE,
        related_name="litigations",
    )
    case_type = models.CharField(
        max_length=20,
        choices=CASE_TYPE_CHOICES,
        verbose_name="Case Type",
        help_text="Schedule VI, Part A, Clause 17(a)",
    )
    party_involved = models.CharField(
        max_length=500,
        verbose_name="Party Involved",
        help_text="Schedule VI, Part A, Clause 17(b)",
    )
    court_or_authority = models.CharField(
        max_length=500,
        verbose_name="Court / Authority / Forum",
        help_text="Schedule VI, Part A, Clause 17(c)",
    )
    status = models.CharField(
        max_length=1000,
        verbose_name="Current Status",
        help_text="Schedule VI, Part A, Clause 17(d)",
    )
    amount_involved = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Amount Involved (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 17(e)",
    )

    class Meta:
        verbose_name = "Litigation Entry"
        verbose_name_plural = "Litigation Entries"
        db_table = "trinity_litigation_entries"
        ordering = ("case_type", "-created_at")

    def __str__(self):
        return f"{self.get_case_type_display()}: {self.party_involved[:60]}"


# ---------------------------------------------------------------------------
# Section 5 — Financial Summary
# ---------------------------------------------------------------------------


class FinancialYearSummary(BaseModel):
    """
    Basic financial figures for one financial year.
    ICDR Reference: Schedule VI, Part A, Clause 10
    """

    ipo_workspace = models.ForeignKey(
        IPOWorkspace,
        on_delete=models.CASCADE,
        related_name="financial_summaries",
    )
    financial_year = models.CharField(
        max_length=9,
        verbose_name="Financial Year",
        help_text="Format: YYYY-YYYY (e.g., 2023-2024). Schedule VI, Part A, Clause 10(a).",
    )
    revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Revenue from Operations (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 10(b)",
    )
    ebitda = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="EBITDA (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 10(c)",
    )
    pat = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Profit After Tax (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 10(d)",
    )
    net_worth = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Net Worth (₹ in Lakhs)",
        help_text="Schedule VI, Part A, Clause 10(e), read with Regulation 229(2)(b)",
    )

    class Meta:
        verbose_name = "Financial Year Summary"
        verbose_name_plural = "Financial Year Summaries"
        db_table = "trinity_financial_year_summaries"
        unique_together = [("ipo_workspace", "financial_year", "deleted_at")]
        constraints = [
            models.UniqueConstraint(
                fields=["ipo_workspace", "financial_year"],
                condition=models.Q(deleted_at__isnull=True),
                name="trinity_fy_summary_unique_workspace_fy_when_not_deleted",
            )
        ]
        ordering = ("-financial_year",)

    def __str__(self):
        return f"FY {self.financial_year} — Rev: ₹{self.revenue}L"


# ---------------------------------------------------------------------------
# Validation Flags — deterministic rule engine output
# ---------------------------------------------------------------------------


class ValidationFlag(BaseModel):
    """
    Stores a single validation flag produced by the deterministic rule engine.
    Flags are regenerated each time the validation endpoint is called.

    Every flag links to a specific rule, severity, regulation citation, and the
    actual data that triggered it — enabling a consolidated compliance report.
    """

    SEVERITY_CHOICES = [
        ("blocking", "Blocking — must be resolved before submission"),
        ("warning", "Warning — review recommended"),
        ("info", "Informational — for awareness"),
    ]

    ipo_workspace = models.ForeignKey(
        IPOWorkspace,
        on_delete=models.CASCADE,
        related_name="validation_flags",
    )
    rule_id = models.CharField(
        max_length=100,
        verbose_name="Rule Identifier",
        help_text="Machine-readable rule identifier, e.g., 'rpt_single_party_threshold'.",
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        verbose_name="Severity Level",
    )
    section = models.CharField(
        max_length=60,
        verbose_name="DRHP Section",
        help_text="Which disclosure section this flag pertains to.",
    )
    field_reference = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Field Reference",
        help_text="Specific field(s) or record(s) involved.",
    )
    message = models.TextField(
        verbose_name="Flag Message",
        help_text="Human-readable explanation of the flag.",
    )
    regulation_citation = models.CharField(
        max_length=255,
        verbose_name="Regulation Citation",
        help_text="ICDR clause or SEBI regulation reference.",
    )
    related_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Related Data",
        help_text="Structured data: actual figures, thresholds, entity names.",
    )

    class Meta:
        verbose_name = "Validation Flag"
        verbose_name_plural = "Validation Flags"
        db_table = "trinity_validation_flags"
        ordering = ("severity", "section", "-created_at")

    def __str__(self):
        return f"[{self.severity.upper()}] {self.rule_id}: {self.message[:80]}"


# ---------------------------------------------------------------------------
# Section Drafts — versioned LLM-generated narrative text
# ---------------------------------------------------------------------------


class SectionDraft(BaseModel):
    """
    Stores a versioned narrative draft for one DRHP disclosure section.

    Drafts are never overwritten — each regeneration creates a new version.
    The data_snapshot and flags_at_generation fields capture exactly what
    the LLM saw when the draft was produced, for audit purposes.
    """

    SECTION_CHOICES = [
        ("objects_of_issue", "Objects of the Issue"),
        ("related_party_transactions", "Related Party Transactions"),
    ]

    ipo_workspace = models.ForeignKey(
        IPOWorkspace,
        on_delete=models.CASCADE,
        related_name="section_drafts",
    )
    section = models.CharField(
        max_length=60,
        choices=SECTION_CHOICES,
        verbose_name="DRHP Section",
    )
    version = models.PositiveIntegerField(
        verbose_name="Draft Version",
        help_text="Auto-incremented per workspace + section.",
    )
    narrative_text = models.TextField(
        verbose_name="Generated Narrative",
        help_text="The LLM-generated prose text for this section.",
    )
    prompt_template_version = models.CharField(
        max_length=20,
        verbose_name="Prompt Template Version",
        help_text="Which versioned template was used (e.g., 'v1').",
    )
    data_snapshot = models.JSONField(
        default=dict,
        verbose_name="Data Snapshot",
        help_text="Complete snapshot of the structured data fed to the LLM.",
    )
    flags_at_generation = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Flags at Generation Time",
        help_text="Warning/info validation flags active when draft was generated.",
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Generated At",
    )

    class Meta:
        verbose_name = "Section Draft"
        verbose_name_plural = "Section Drafts"
        db_table = "trinity_section_drafts"
        ordering = ("section", "-version")
        unique_together = ("ipo_workspace", "section", "version")

    def __str__(self):
        return f"{self.get_section_display()} v{self.version} — {self.ipo_workspace}"

