"""
Trinity Drafting Layer — Unit Tests

Tests narrative generation constraints, template formatting, blocking validation
flag enforcement, versioning, and database persistence.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from decimal import Decimal

from plane.db.models import User, Workspace
from plane.trinity.models import (
    IPOWorkspace,
    ObjectsOfIssue,
    UseOfProceeds,
    SectionDraft,
    ValidationFlag,
)
from plane.trinity.drafting.service import generate_draft


class TestDraftingLayer(TestCase):

    def setUp(self):
        # Create user and workspace manually
        self.user = User.objects.create(
            email="testowner@example.com",
            first_name="Test",
            last_name="Owner",
        )
        self.workspace = Workspace.objects.create(
            name="Test Workspace",
            slug="test",
            owner=self.user,
        )
        self.ipo_workspace = IPOWorkspace.objects.create(
            workspace=self.workspace,
            company_name="Trinity SME Ltd",
            cin="U12345DL2026PLC123456",
            exchange_target="nse_emerge",
        )

    @patch("plane.trinity.drafting.service.run_validation")
    @patch("plane.trinity.drafting.service.get_llm_config")
    @patch("plane.trinity.drafting.service.get_llm_response")
    def test_drafting_successful_generation(self, mock_get_response, mock_get_config, mock_run_val):
        """Tests that a draft is successfully generated when no blocking flags exist."""
        mock_get_config.return_value = ("mock-key", "gpt-4o-mini", "openai")
        mock_get_response.return_value = ("This is the generated narrative draft.", None)
        
        # Return empty flags from validator
        mock_run_val.return_value = ValidationFlag.objects.none()

        # Set up a few use of proceeds items (Objects of the Issue)
        ooi = ObjectsOfIssue.objects.create(
            ipo_workspace=self.ipo_workspace,
            fresh_issue_amount=Decimal("500.00"),
        )
        UseOfProceeds.objects.create(
            objects_of_issue=ooi,
            category="capex",
            amount=Decimal("300.00"),
            justification="Purchase of machinery",
        )

        draft = generate_draft(self.ipo_workspace, "objects_of_issue")

        # Verify database record
        self.assertEqual(draft.version, 1)
        self.assertEqual(draft.section, "objects_of_issue")
        self.assertEqual(draft.narrative_text, "This is the generated narrative draft.")
        self.assertEqual(draft.prompt_template_version, "v1")
        self.assertEqual(draft.data_snapshot["company_name"], "Trinity SME Ltd")
        self.assertEqual(
            draft.data_snapshot["objects_of_issue"]["fresh_issue_amount"],
            500.0,
        )

        # Verify consecutive draft auto-increments version
        mock_get_response.return_value = ("Version 2 draft.", None)
        draft2 = generate_draft(self.ipo_workspace, "objects_of_issue")
        self.assertEqual(draft2.version, 2)
        self.assertEqual(draft2.narrative_text, "Version 2 draft.")

    @patch("plane.trinity.drafting.service.run_validation")
    @patch("plane.trinity.drafting.service.get_llm_config")
    @patch("plane.trinity.drafting.service.get_llm_response")
    def test_constraint_1_missing_fields_have_missing_markers(self, mock_get_response, mock_get_config, mock_run_val):
        """Constraint 1: Verify the prompt contains [MISSING: ...] markers for unset fields."""
        mock_get_config.return_value = ("mock-key", "gpt-4o-mini", "openai")
        mock_get_response.return_value = ("Draft", None)
        mock_run_val.return_value = ValidationFlag.objects.none()

        # Leave company_name and CIN empty
        self.ipo_workspace.company_name = ""
        self.ipo_workspace.cin = ""
        self.ipo_workspace.save()

        # Create ObjectsOfIssue but keep fresh_issue_amount None
        ObjectsOfIssue.objects.create(
            ipo_workspace=self.ipo_workspace,
            fresh_issue_amount=None,
        )

        # We'll capture the prompt sent to the LLM
        generate_draft(self.ipo_workspace, "objects_of_issue")

        called_args = mock_get_response.call_args[0]
        prompt_text = called_args[1]

        self.assertIn("Company Name: [MISSING: company_name]", prompt_text)
        self.assertIn("CIN: [MISSING: cin]", prompt_text)
        self.assertIn("Fresh Issue Amount: ₹[MISSING: fresh_issue_amount] Lakhs", prompt_text)

    @patch("plane.trinity.drafting.service.run_validation")
    @patch("plane.trinity.drafting.service.get_llm_config")
    @patch("plane.trinity.drafting.service.get_llm_response")
    def test_constraint_2_only_preconfigured_citations_present(self, mock_get_response, mock_get_config, mock_run_val):
        """Constraint 2: Verify the metadata only lists preconfigured schema regulation references."""
        mock_get_config.return_value = ("mock-key", "gpt-4o-mini", "openai")
        mock_get_response.return_value = ("Draft", None)
        mock_run_val.return_value = ValidationFlag.objects.none()

        generate_draft(self.ipo_workspace, "related_party_transactions")

        called_args = mock_get_response.call_args[0]
        prompt_text = called_args[1]

        # Verify that it contains references from related_party_transactions.json schema file
        self.assertIn("Schedule VI, Part A, Clause 14", prompt_text)

    @patch("plane.trinity.drafting.service.run_validation")
    @patch("plane.trinity.drafting.service.get_llm_config")
    @patch("plane.trinity.drafting.service.get_llm_response")
    def test_constraint_3_refuses_on_blocking_flags(self, mock_get_response, mock_get_config, mock_run_val):
        """Constraint 3: Refuse to generate draft if a blocking flag exists for the section."""
        mock_get_config.return_value = ("mock-key", "gpt-4o-mini", "openai")
        
        # Mock run_validation to return a queryset containing a blocking flag
        blocking_flag = ValidationFlag(
            ipo_workspace=self.ipo_workspace,
            rule_id="test_blocking_rule",
            severity="blocking",
            section="objects_of_issue",
            message="Blocking issue: GCP exceeds cap",
            regulation_citation="Some citation",
        )
        # Wrap in a list and mock a queryset-like behavior or filter method
        mock_qs = MagicMock()
        mock_qs.filter.return_value.exists.return_value = True
        mock_qs.filter.return_value.__iter__.return_value = [blocking_flag]
        mock_run_val.return_value = mock_qs

        with self.assertRaises(ValueError) as ctx:
            generate_draft(self.ipo_workspace, "objects_of_issue")

        self.assertIn("GCP exceeds cap", str(ctx.exception))
        mock_get_response.assert_not_called()

    @patch("plane.trinity.drafting.service.run_validation")
    @patch("plane.trinity.drafting.service.get_llm_config")
    @patch("plane.trinity.drafting.service.get_llm_response")
    def test_warning_flags_passed_as_context(self, mock_get_response, mock_get_config, mock_run_val):
        """Verify that warning/info flags are passed to the prompt as caveats."""
        mock_get_config.return_value = ("mock-key", "gpt-4o-mini", "openai")
        mock_get_response.return_value = ("Draft", None)

        # Mock run_validation to return a warning flag
        warning_flag = ValidationFlag(
            ipo_workspace=self.ipo_workspace,
            rule_id="test_warning_rule",
            severity="warning",
            section="related_party_transactions",
            message="Warning: RPT exceeds 10% revenue",
            regulation_citation="Clause 14(d)",
        )
        mock_qs = MagicMock()
        # filter(severity="blocking", ...) -> return empty mock (no blocking flags)
        # filter(severity__in=["warning", "info"], ...) -> return warning_flag list
        def side_effect_filter(*args, **kwargs):
            inner_mock = MagicMock()
            if kwargs.get("severity") == "blocking":
                inner_mock.exists.return_value = False
                inner_mock.__iter__.return_value = []
            else:
                inner_mock.exists.return_value = True
                inner_mock.__iter__.return_value = [warning_flag]
            return inner_mock

        mock_qs.filter.side_effect = side_effect_filter
        mock_run_val.return_value = mock_qs

        generate_draft(self.ipo_workspace, "related_party_transactions")

        called_args = mock_get_response.call_args[0]
        prompt_text = called_args[1]

        self.assertIn("[WARNING] Warning: RPT exceeds 10% revenue", prompt_text)
        self.assertIn("Clause 14(d)", prompt_text)
