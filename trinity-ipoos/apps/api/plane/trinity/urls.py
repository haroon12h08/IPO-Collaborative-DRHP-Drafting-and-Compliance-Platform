"""
Trinity IPO Preparation Tool — URL patterns

All endpoints are workspace-scoped via the <slug> parameter,
which maps to Plane's existing workspace slug.
"""

from django.urls import path

from .views import (
    ICDRSchemaEndpoint,
    IPOWorkspaceEndpoint,
    ObjectsOfIssueEndpoint,
    RelatedPartyTransactionEndpoint,
    ShareholderEntryEndpoint,
    LitigationEntryEndpoint,
    FinancialYearSummaryEndpoint,
    ValidationEndpoint,
    DraftingEndpoint,
)

urlpatterns = [
    # ICDR Schemas (read-only)
    path(
        "workspaces/<str:slug>/schemas/",
        ICDRSchemaEndpoint.as_view(),
        name="trinity-schemas-list",
    ),
    path(
        "workspaces/<str:slug>/schemas/<str:section_id>/",
        ICDRSchemaEndpoint.as_view(),
        name="trinity-schemas-detail",
    ),
    # IPO Workspace
    path(
        "workspaces/<str:slug>/",
        IPOWorkspaceEndpoint.as_view(),
        name="trinity-ipo-workspace",
    ),
    # Section 1 — Objects of the Issue (single resource, upsert)
    path(
        "workspaces/<str:slug>/objects-of-issue/",
        ObjectsOfIssueEndpoint.as_view(),
        name="trinity-objects-of-issue",
    ),
    # Section 2 — Related Party Transactions (CRUD collection)
    path(
        "workspaces/<str:slug>/related-party-transactions/",
        RelatedPartyTransactionEndpoint.as_view({"get": "list", "post": "create"}),
        name="trinity-rpt-list",
    ),
    path(
        "workspaces/<str:slug>/related-party-transactions/<uuid:pk>/",
        RelatedPartyTransactionEndpoint.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="trinity-rpt-detail",
    ),
    # Section 3 — Capital Structure / Shareholders (CRUD collection)
    path(
        "workspaces/<str:slug>/shareholders/",
        ShareholderEntryEndpoint.as_view({"get": "list", "post": "create"}),
        name="trinity-shareholder-list",
    ),
    path(
        "workspaces/<str:slug>/shareholders/<uuid:pk>/",
        ShareholderEntryEndpoint.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="trinity-shareholder-detail",
    ),
    # Section 4 — Litigation (CRUD collection)
    path(
        "workspaces/<str:slug>/litigations/",
        LitigationEntryEndpoint.as_view({"get": "list", "post": "create"}),
        name="trinity-litigation-list",
    ),
    path(
        "workspaces/<str:slug>/litigations/<uuid:pk>/",
        LitigationEntryEndpoint.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="trinity-litigation-detail",
    ),
    # Section 5 — Financial Summary (CRUD collection)
    path(
        "workspaces/<str:slug>/financials/",
        FinancialYearSummaryEndpoint.as_view({"get": "list", "post": "create"}),
        name="trinity-financials-list",
    ),
    path(
        "workspaces/<str:slug>/financials/<uuid:pk>/",
        FinancialYearSummaryEndpoint.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="trinity-financials-detail",
    ),
    # Validation Engine (GET = cached flags, POST = fresh run)
    path(
        "workspaces/<str:slug>/validate/",
        ValidationEndpoint.as_view(),
        name="trinity-validate",
    ),
    # Narrative Drafting (GET = list versions, POST = run drafting)
    path(
        "workspaces/<str:slug>/draft/<str:section>/",
        DraftingEndpoint.as_view(),
        name="trinity-draft",
    ),
]

