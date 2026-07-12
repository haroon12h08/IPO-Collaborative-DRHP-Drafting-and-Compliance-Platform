"""
Trinity IPO Preparation Tool — DRF Serializers

Each serializer follows Plane's existing BaseSerializer pattern.
Nested serializers are used for the Objects of Issue section (header + line items).
"""

from rest_framework import serializers

from plane.app.serializers.base import BaseSerializer

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


# ---------------------------------------------------------------------------
# IPO Workspace
# ---------------------------------------------------------------------------


class IPOWorkspaceSerializer(BaseSerializer):
    # Read-only computed fields
    sections_status = serializers.SerializerMethodField()

    class Meta:
        model = IPOWorkspace
        fields = "__all__"
        read_only_fields = ["workspace", "created_by", "updated_by"]

    def get_sections_status(self, obj):
        """Returns completion status for each section."""
        return {
            "objects_of_issue": hasattr(obj, "objects_of_issue"),
            "related_party_transactions": obj.related_party_transactions.exists(),
            "capital_structure": obj.shareholders.exists(),
            "litigation": obj.litigations.exists(),
            "financial_summary": obj.financial_summaries.exists(),
        }


# ---------------------------------------------------------------------------
# Section 1 — Objects of the Issue
# ---------------------------------------------------------------------------


class UseOfProceedsSerializer(BaseSerializer):
    class Meta:
        model = UseOfProceeds
        fields = "__all__"
        read_only_fields = ["objects_of_issue", "created_by", "updated_by"]


class ObjectsOfIssueSerializer(BaseSerializer):
    use_of_proceeds = UseOfProceedsSerializer(many=True, read_only=True)

    class Meta:
        model = ObjectsOfIssue
        fields = "__all__"
        read_only_fields = ["ipo_workspace", "created_by", "updated_by"]


class ObjectsOfIssueWriteSerializer(BaseSerializer):
    """
    Handles create/update with nested use_of_proceeds line items.
    Accepts an array of line items in the request body and manages them
    as a batch (create/update/delete as needed).
    """

    use_of_proceeds = UseOfProceedsSerializer(many=True, required=False)

    class Meta:
        model = ObjectsOfIssue
        fields = "__all__"
        read_only_fields = ["ipo_workspace", "created_by", "updated_by"]

    def create(self, validated_data):
        line_items_data = validated_data.pop("use_of_proceeds", [])
        obj = ObjectsOfIssue.objects.create(**validated_data)
        for item_data in line_items_data:
            UseOfProceeds.objects.create(objects_of_issue=obj, **item_data)
        return obj

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop("use_of_proceeds", None)
        # Update header fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If line_items_data is provided, reconcile
        if line_items_data is not None:
            existing_ids = set(
                instance.use_of_proceeds.values_list("id", flat=True)
            )
            incoming_ids = set()

            for item_data in line_items_data:
                item_id = item_data.pop("id", None)
                if item_id and item_id in existing_ids:
                    # Update existing
                    UseOfProceeds.objects.filter(id=item_id).update(**item_data)
                    incoming_ids.add(item_id)
                else:
                    # Create new
                    new_item = UseOfProceeds.objects.create(
                        objects_of_issue=instance, **item_data
                    )
                    incoming_ids.add(new_item.id)

            # Soft-delete removed items
            removed_ids = existing_ids - incoming_ids
            if removed_ids:
                for item in UseOfProceeds.objects.filter(id__in=removed_ids):
                    item.delete(soft=True)

        return instance


# ---------------------------------------------------------------------------
# Section 2 — Related Party Transactions
# ---------------------------------------------------------------------------


class RelatedPartyTransactionSerializer(BaseSerializer):
    class Meta:
        model = RelatedPartyTransaction
        fields = "__all__"
        read_only_fields = ["ipo_workspace", "created_by", "updated_by"]


# ---------------------------------------------------------------------------
# Section 3 — Capital Structure / Promoter Shareholding
# ---------------------------------------------------------------------------


class ShareholderEntrySerializer(BaseSerializer):
    class Meta:
        model = ShareholderEntry
        fields = "__all__"
        read_only_fields = ["ipo_workspace", "created_by", "updated_by"]


# ---------------------------------------------------------------------------
# Section 4 — Litigation & Regulatory Actions
# ---------------------------------------------------------------------------


class LitigationEntrySerializer(BaseSerializer):
    class Meta:
        model = LitigationEntry
        fields = "__all__"
        read_only_fields = ["ipo_workspace", "created_by", "updated_by"]


# ---------------------------------------------------------------------------
# Section 5 — Financial Summary
# ---------------------------------------------------------------------------


class FinancialYearSummarySerializer(BaseSerializer):
    class Meta:
        model = FinancialYearSummary
        fields = "__all__"
        read_only_fields = ["ipo_workspace", "created_by", "updated_by"]


# ---------------------------------------------------------------------------
# Validation Flags
# ---------------------------------------------------------------------------


class ValidationFlagSerializer(BaseSerializer):
    class Meta:
        model = ValidationFlag
        fields = [
            "id",
            "rule_id",
            "severity",
            "section",
            "field_reference",
            "message",
            "regulation_citation",
            "related_data",
            "created_at",
        ]
        read_only_fields = fields


class ValidationSummarySerializer(serializers.Serializer):
    """Read-only summary of the validation run."""
    total_flags = serializers.IntegerField()
    blocking = serializers.IntegerField()
    warning = serializers.IntegerField()
    info = serializers.IntegerField()
    flags = ValidationFlagSerializer(many=True)
    validated_at = serializers.DateTimeField()


# ---------------------------------------------------------------------------
# Section Drafts
# ---------------------------------------------------------------------------


class SectionDraftSerializer(BaseSerializer):
    class Meta:
        model = SectionDraft
        fields = [
            "id",
            "section",
            "version",
            "narrative_text",
            "prompt_template_version",
            "data_snapshot",
            "flags_at_generation",
            "generated_at",
        ]
        read_only_fields = fields

