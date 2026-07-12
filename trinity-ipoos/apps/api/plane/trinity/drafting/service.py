"""
Trinity Drafting Service — Narrative prose generation using LLM

Checks for blocking flags, prepares versioned prompt templates, gathers
structured data and schema metadata, calls the configured LLM, and persists
the draft version.
"""

import os
import json
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from plane.app.views.external.base import get_llm_config, get_llm_response
from plane.trinity.models import (
    IPOWorkspace,
    ObjectsOfIssue,
    UseOfProceeds,
    RelatedPartyTransaction,
    ShareholderEntry,
    SectionDraft,
    ValidationFlag,
)
from plane.trinity.validators.engine import run_validation

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas")


def _get_schema_metadata(section_id: str) -> str:
    """Reads required ICDR clause citations from the JSON schema file."""
    filepath = os.path.join(SCHEMAS_DIR, f"{section_id}.json")
    if not os.path.exists(filepath):
        return "[MISSING: Schema metadata]"

    try:
        with open(filepath, "r") as f:
            schema = json.load(f)

        metadata = []
        metadata.append(f"Section Title: {schema.get('section_title', '')}")
        metadata.append(f"Regulation Reference: {schema.get('regulation_reference', '')}")
        metadata.append(f"Description: {schema.get('description', '')}")

        # Field-level citations
        metadata.append("\nField Regulations:")
        for name, field_def in schema.get("fields", {}).items():
            clause = field_def.get("icdr_clause", "")
            text = field_def.get("icdr_text", "")
            if clause:
                metadata.append(f"- {name}: {clause} ({text})")

        # Line-item citations (for Objects of the Issue)
        if "line_item_fields" in schema:
            metadata.append("\nLine Item Regulations:")
            for name, field_def in schema.get("line_item_fields", {}).items():
                clause = field_def.get("icdr_clause", "")
                text = field_def.get("icdr_text", "")
                if clause:
                    metadata.append(f"- {name}: {clause} ({text})")

        return "\n".join(metadata)
    except Exception:
        return "[MISSING: Failed to parse schema metadata]"


def _serialize_decimal(val):
    if isinstance(val, Decimal):
        return float(val)
    return val


def generate_draft(ipo_workspace: IPOWorkspace, section: str, prompt_version: str = "v1"):
    """
    Generates a versioned prose draft for a given section.
    1. Runs validation engine first.
    2. If there are blocking flags for the target section, raises ValueError with blocking flags.
    3. Gathers structured data & warning/info flags.
    4. Renders prompt template.
    5. Invokes Plane's configured LLM.
    6. Saves new SectionDraft to database.
    """
    # 1. Run/Retrieve validation
    flags_qs = run_validation(ipo_workspace)

    # 2. Check for blocking flags for this specific section (or cross_section)
    blocking_flags = flags_qs.filter(
        severity="blocking",
        section__in=[section, "cross_section"]
    )

    if blocking_flags.exists():
        # Raise an exception containing the blocking flag messages
        flag_messages = [f.message for f in blocking_flags]
        raise ValueError(
            f"Cannot generate narrative draft. Resolving blocking validation flags first is required: {'; '.join(flag_messages)}"
        )

    # Gather warning & info flags to pass as caveats
    caveats = flags_qs.filter(
        severity__in=["warning", "info"],
        section__in=[section, "cross_section"]
    )
    flags_data = []
    flags_text_list = []
    for flag in caveats:
        flags_data.append({
            "rule_id": flag.rule_id,
            "severity": flag.severity,
            "message": flag.message,
            "regulation_citation": flag.regulation_citation,
        })
        flags_text_list.append(
            f"- [{flag.severity.upper()}] {flag.message} (Citation: {flag.regulation_citation})"
        )
    flags_text = "\n".join(flags_text_list) if flags_text_list else "No active validation warnings or advisories for this section."

    # Load prompt template
    template_path = os.path.join(PROMPTS_DIR, prompt_version, f"{section}.txt")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    with open(template_path, "r") as f:
        prompt_template = f.read()

    # Load schema metadata
    schema_metadata = _get_schema_metadata(section)

    # 3. Gather section-specific structured data & build prompt parameters
    prompt_params = {
        "schema_metadata": schema_metadata,
        "company_name": ipo_workspace.company_name or "[MISSING: company_name]",
        "cin": ipo_workspace.cin or "[MISSING: cin]",
        "flags_text": flags_text,
    }
    data_snapshot = {
        "company_name": ipo_workspace.company_name,
        "cin": ipo_workspace.cin,
        "exchange_target": ipo_workspace.exchange_target,
    }

    if section == "objects_of_issue":
        try:
            ooi = ObjectsOfIssue.objects.get(ipo_workspace=ipo_workspace)
            fresh_issue_amount = ooi.fresh_issue_amount
        except ObjectsOfIssue.DoesNotExist:
            ooi = None
            fresh_issue_amount = None

        prompt_params["exchange_target"] = ipo_workspace.get_exchange_target_display()
        prompt_params["fresh_issue_amount"] = (
            str(fresh_issue_amount) if fresh_issue_amount is not None else "[MISSING: fresh_issue_amount]"
        )

        use_of_proceeds = list(UseOfProceeds.objects.filter(objects_of_issue=ooi)) if ooi else []
        uop_texts = []
        uop_data = []

        if not use_of_proceeds:
            uop_texts.append("- [MISSING: No use of proceeds line items provided]")
        else:
            for idx, item in enumerate(use_of_proceeds, 1):
                cat_display = item.get_category_display()
                amt_str = str(item.amount) if item.amount is not None else "[MISSING: amount]"
                just_str = item.justification.strip() if item.justification else "[MISSING: justification]"
                uop_texts.append(
                    f"{idx}. Category: {cat_display}\n"
                    f"   Allocation Amount: ₹{amt_str} Lakhs\n"
                    f"   Justification/Rationale: {just_str}"
                )
                uop_data.append({
                    "category": item.category,
                    "amount": _serialize_decimal(item.amount),
                    "justification": item.justification,
                })

        prompt_params["use_of_proceeds_text"] = "\n\n".join(uop_texts)

        # Snapshot structure
        data_snapshot["objects_of_issue"] = {
            "fresh_issue_amount": _serialize_decimal(fresh_issue_amount),
            "use_of_proceeds": uop_data,
        }

    elif section == "related_party_transactions":
        rpts = list(RelatedPartyTransaction.objects.filter(ipo_workspace=ipo_workspace))
        rpt_texts = []
        rpt_data = []

        if not rpts:
            rpt_texts.append("- [MISSING: No related party transactions entered]")
        else:
            for idx, rpt in enumerate(rpts, 1):
                name_str = rpt.related_party_name or "[MISSING: related_party_name]"
                rel_display = rpt.get_relationship_type_display() if rpt.relationship_type else "[MISSING: relationship_type]"
                type_str = rpt.transaction_type or "[MISSING: transaction_type]"
                amt_str = str(rpt.amount) if rpt.amount is not None else "[MISSING: amount]"
                fy_str = rpt.financial_year or "[MISSING: financial_year]"
                arms_length_str = "Yes" if rpt.is_arms_length else "No"

                rpt_texts.append(
                    f"{idx}. Related Party: {name_str}\n"
                    f"   Relationship: {rel_display}\n"
                    f"   Transaction Type: {type_str}\n"
                    f"   Financial Year: {fy_str}\n"
                    f"   Amount: ₹{amt_str} Lakhs\n"
                    f"   At Arm's Length: {arms_length_str}"
                )
                rpt_data.append({
                    "related_party_name": rpt.related_party_name,
                    "relationship_type": rpt.relationship_type,
                    "transaction_type": rpt.transaction_type,
                    "amount": _serialize_decimal(rpt.amount),
                    "financial_year": rpt.financial_year,
                    "is_arms_length": rpt.is_arms_length,
                })

        prompt_params["rpt_text"] = "\n\n".join(rpt_texts)
        data_snapshot["related_party_transactions"] = rpt_data

    else:
        raise ValueError(f"Drafting not supported for section: {section}")

    # RENDER PROMPT
    final_prompt = prompt_template.format(**prompt_params)

    # 4. Invoke LLM via Plane external AI settings
    api_key, model, provider = get_llm_config()
    if not api_key or not model or not provider:
        raise ValueError(
            "Plane LLM configuration is missing or incomplete (LLM_API_KEY, LLM_PROVIDER, LLM_MODEL)."
        )

    task_desc = f"Draft DRHP disclosure narrative for section: {section} using ONLY the provided structured data."
    text, error = get_llm_response(task_desc, final_prompt, api_key, model, provider)
    if error or not text:
        raise RuntimeError(f"LLM Generation failed: {error or 'Empty response'}")

    # 5. Versioning logic
    last_draft = SectionDraft.objects.filter(
        ipo_workspace=ipo_workspace,
        section=section
    ).order_by("-version").first()
    new_version = (last_draft.version + 1) if last_draft else 1

    # 6. Save Draft
    draft = SectionDraft.objects.create(
        ipo_workspace=ipo_workspace,
        section=section,
        version=new_version,
        narrative_text=text,
        prompt_template_version=prompt_version,
        data_snapshot=data_snapshot,
        flags_at_generation=flags_data,
    )

    return draft
