"""
Trinity IPO Preparation Tool — API Views

Uses Plane's existing BaseViewSet / BaseAPIView and permission classes.
All endpoints are workspace-scoped (identified by slug in the URL).
"""

import json
import os

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from plane.app.permissions.workspace import (
    WorkspaceEntityPermission,
    WorkspaceViewerPermission,
)
from plane.app.views.base import BaseAPIView, BaseViewSet
from plane.db.models import Workspace

from .models import (
    IPOWorkspace,
    ObjectsOfIssue,
    UseOfProceeds,
    RelatedPartyTransaction,
    ShareholderEntry,
    LitigationEntry,
    FinancialYearSummary,
    ValidationFlag,
    SectionDraft,
)
from .serializers import (
    IPOWorkspaceSerializer,
    ObjectsOfIssueSerializer,
    ObjectsOfIssueWriteSerializer,
    UseOfProceedsSerializer,
    RelatedPartyTransactionSerializer,
    ShareholderEntrySerializer,
    LitigationEntrySerializer,
    FinancialYearSummarySerializer,
    ValidationFlagSerializer,
    SectionDraftSerializer,
)
from .validators.engine import run_validation
from .drafting.service import generate_draft


# ---------------------------------------------------------------------------
# Helper: resolve IPO workspace from URL slug
# ---------------------------------------------------------------------------

def _get_ipo_workspace(slug):
    """Get or 404 the IPOWorkspace for a given workspace slug."""
    workspace = Workspace.objects.get(slug=slug)
    return IPOWorkspace.objects.get(workspace=workspace)


# ---------------------------------------------------------------------------
# ICDR Schema endpoint — serves the JSON schema files to the frontend
# ---------------------------------------------------------------------------

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


class ICDRSchemaEndpoint(BaseAPIView):
    """
    GET /api/trinity/workspaces/<slug>/schemas/
    GET /api/trinity/workspaces/<slug>/schemas/<section_id>/

    Returns ICDR clause metadata schemas. Read-only.
    Any workspace member can view.
    """

    permission_classes = [WorkspaceViewerPermission]

    def get(self, request, slug, section_id=None):
        if section_id:
            filepath = os.path.join(SCHEMA_DIR, f"{section_id}.json")
            if not os.path.exists(filepath):
                return Response(
                    {"error": f"Schema '{section_id}' not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            with open(filepath, "r") as f:
                return Response(json.load(f))

        # Return all schemas
        schemas = {}
        for filename in sorted(os.listdir(SCHEMA_DIR)):
            if filename.endswith(".json"):
                with open(os.path.join(SCHEMA_DIR, filename), "r") as f:
                    key = filename.replace(".json", "")
                    schemas[key] = json.load(f)
        return Response(schemas)


# ---------------------------------------------------------------------------
# IPO Workspace CRUD
# ---------------------------------------------------------------------------


class IPOWorkspaceEndpoint(BaseAPIView):
    """
    GET  /api/trinity/workspaces/<slug>/  — retrieve IPO workspace
    POST /api/trinity/workspaces/<slug>/  — create (initialize) IPO workspace
    PATCH /api/trinity/workspaces/<slug>/ — update IPO workspace
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        try:
            ipo_ws = _get_ipo_workspace(slug)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return Response(
                {"exists": False},
                status=status.HTTP_200_OK,
            )
        serializer = IPOWorkspaceSerializer(ipo_ws)
        return Response({"exists": True, **serializer.data})

    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        if IPOWorkspace.objects.filter(workspace=workspace).exists():
            return Response(
                {"error": "IPO workspace already exists for this workspace."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = IPOWorkspaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(workspace=workspace)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, slug):
        ipo_ws = _get_ipo_workspace(slug)
        serializer = IPOWorkspaceSerializer(ipo_ws, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Section 1 — Objects of the Issue
# ---------------------------------------------------------------------------


class ObjectsOfIssueEndpoint(BaseAPIView):
    """
    GET   — retrieve objects of the issue with nested use_of_proceeds
    POST  — create or update (upsert) with nested line items
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        try:
            ipo_ws = _get_ipo_workspace(slug)
            obj = ObjectsOfIssue.objects.get(ipo_workspace=ipo_ws)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist, ObjectsOfIssue.DoesNotExist):
            return Response({"exists": False}, status=status.HTTP_200_OK)
        serializer = ObjectsOfIssueSerializer(obj)
        return Response({"exists": True, **serializer.data})

    def post(self, request, slug):
        ipo_ws = _get_ipo_workspace(slug)
        try:
            existing = ObjectsOfIssue.objects.get(ipo_workspace=ipo_ws)
            serializer = ObjectsOfIssueWriteSerializer(
                existing, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                ObjectsOfIssueSerializer(existing).data,
                status=status.HTTP_200_OK,
            )
        except ObjectsOfIssue.DoesNotExist:
            serializer = ObjectsOfIssueWriteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(ipo_workspace=ipo_ws)
            return Response(
                ObjectsOfIssueSerializer(serializer.instance).data,
                status=status.HTTP_201_CREATED,
            )


# ---------------------------------------------------------------------------
# Section 2 — Related Party Transactions (list/create/update/delete)
# ---------------------------------------------------------------------------


class RelatedPartyTransactionEndpoint(BaseViewSet):
    model = RelatedPartyTransaction
    serializer_class = RelatedPartyTransactionSerializer
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        try:
            ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
            return RelatedPartyTransaction.objects.filter(ipo_workspace=ipo_ws)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return RelatedPartyTransaction.objects.none()

    def perform_create(self, serializer):
        ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
        serializer.save(ipo_workspace=ipo_ws)


# ---------------------------------------------------------------------------
# Section 3 — Capital Structure / Shareholders
# ---------------------------------------------------------------------------


class ShareholderEntryEndpoint(BaseViewSet):
    model = ShareholderEntry
    serializer_class = ShareholderEntrySerializer
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        try:
            ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
            return ShareholderEntry.objects.filter(ipo_workspace=ipo_ws)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return ShareholderEntry.objects.none()

    def perform_create(self, serializer):
        ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
        serializer.save(ipo_workspace=ipo_ws)


# ---------------------------------------------------------------------------
# Section 4 — Litigation
# ---------------------------------------------------------------------------


class LitigationEntryEndpoint(BaseViewSet):
    model = LitigationEntry
    serializer_class = LitigationEntrySerializer
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        try:
            ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
            return LitigationEntry.objects.filter(ipo_workspace=ipo_ws)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return LitigationEntry.objects.none()

    def perform_create(self, serializer):
        ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
        serializer.save(ipo_workspace=ipo_ws)


# ---------------------------------------------------------------------------
# Section 5 — Financial Summary
# ---------------------------------------------------------------------------


class FinancialYearSummaryEndpoint(BaseViewSet):
    model = FinancialYearSummary
    serializer_class = FinancialYearSummarySerializer
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        try:
            ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
            return FinancialYearSummary.objects.filter(ipo_workspace=ipo_ws)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return FinancialYearSummary.objects.none()

    def perform_create(self, serializer):
        ipo_ws = _get_ipo_workspace(self.kwargs["slug"])
        serializer.save(ipo_workspace=ipo_ws)


# ---------------------------------------------------------------------------
# Validation Engine Endpoint
# ---------------------------------------------------------------------------


class ValidationEndpoint(BaseAPIView):
    """
    GET  /api/trinity/workspaces/<slug>/validate/
        Returns the most recently saved validation flags for this workspace.
        If no flags exist yet, returns an empty result set.

    POST /api/trinity/workspaces/<slug>/validate/
        Triggers a fresh validation run: executes all deterministic rules
        against the current workspace data, persists the flags to the
        database, and returns the full flag report.

    All flags are sorted by severity: blocking → warning → info.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        try:
            ipo_ws = _get_ipo_workspace(slug)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return Response(
                {"error": "IPO workspace not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        flags_qs = ValidationFlag.objects.filter(ipo_workspace=ipo_ws)
        flags = list(flags_qs)

        severity_counts = {"blocking": 0, "warning": 0, "info": 0}
        for f in flags:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        # Use the latest flag's created_at as the validation timestamp
        validated_at = flags[0].created_at if flags else None

        return Response({
            "total_flags": len(flags),
            "blocking": severity_counts["blocking"],
            "warning": severity_counts["warning"],
            "info": severity_counts["info"],
            "validated_at": validated_at,
            "flags": ValidationFlagSerializer(flags, many=True).data,
        })

    def post(self, request, slug):
        try:
            ipo_ws = _get_ipo_workspace(slug)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return Response(
                {"error": "IPO workspace not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Run all deterministic validation rules
        flags_qs = run_validation(ipo_ws)
        flags = list(flags_qs)

        severity_counts = {"blocking": 0, "warning": 0, "info": 0}
        for f in flags:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        return Response({
            "total_flags": len(flags),
            "blocking": severity_counts["blocking"],
            "warning": severity_counts["warning"],
            "info": severity_counts["info"],
            "validated_at": timezone.now(),
            "flags": ValidationFlagSerializer(flags, many=True).data,
        })


# ---------------------------------------------------------------------------
# Narrative Drafting Endpoint
# ---------------------------------------------------------------------------


class DraftingEndpoint(BaseAPIView):
    """
    GET  /api/trinity/workspaces/<slug>/draft/<section>/
        Returns all generated draft versions for the given section,
        ordered by version descending (most recent first).

    POST /api/trinity/workspaces/<slug>/draft/<section>/
        Triggers a fresh narrative drafting run for the given section.
        Validates the section first. If any blocking flags exist for this
        section or cross-section, generation is refused with a 400 Bad Request,
        returning the active blocking flags.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug, section):
        if section not in ("objects_of_issue", "related_party_transactions"):
            return Response(
                {"error": f"Drafting not supported for section: {section}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ipo_ws = _get_ipo_workspace(slug)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return Response(
                {"error": "IPO workspace not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        drafts = SectionDraft.objects.filter(ipo_workspace=ipo_ws, section=section)
        return Response(SectionDraftSerializer(drafts, many=True).data)

    def post(self, request, slug, section):
        if section not in ("objects_of_issue", "related_party_transactions"):
            return Response(
                {"error": f"Drafting not supported for section: {section}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ipo_ws = _get_ipo_workspace(slug)
        except (Workspace.DoesNotExist, IPOWorkspace.DoesNotExist):
            return Response(
                {"error": "IPO workspace not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Optional query param or body param to select prompt template version
        prompt_version = request.data.get("prompt_version", "v1")

        try:
            draft = generate_draft(ipo_ws, section, prompt_version)
            return Response(
                SectionDraftSerializer(draft).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            # Re-run validation to return current blocking flags to client
            flags_qs = run_validation(ipo_ws)
            blocking_flags = flags_qs.filter(
                severity="blocking",
                section__in=[section, "cross_section"]
            )
            return Response(
                {
                    "error": str(e),
                    "blocking_flags": ValidationFlagSerializer(blocking_flags, many=True).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Draft generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

