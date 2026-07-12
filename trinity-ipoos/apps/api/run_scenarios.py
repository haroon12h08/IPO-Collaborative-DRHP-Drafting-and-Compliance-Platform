import os
import django
from decimal import Decimal
from datetime import date

# Set settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.local")
django.setup()

# Configure environment variables for OpenAI client to point to Ollama proxy
os.environ["LLM_API_KEY"] = "dummy-key"
os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "http://172.18.0.1:11435/v1"
os.environ["OPENAI_API_KEY"] = "dummy-key"

from plane.db.models import User, Workspace
from plane.license.models import InstanceConfiguration
from plane.trinity.models import (
    IPOWorkspace,
    ObjectsOfIssue,
    UseOfProceeds,
    RelatedPartyTransaction,
    ShareholderEntry,
    SectionDraft,
)
from plane.trinity.drafting.service import generate_draft

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM instance_configurations WHERE key IN ('LLM_API_KEY', 'LLM_PROVIDER', 'LLM_MODEL')")

# Setup LLM configuration in database since SKIP_ENV_VAR is True
InstanceConfiguration.objects.create(
    key="LLM_API_KEY",
    value="dummy-key",
    category="llm",
    is_encrypted=False
)
InstanceConfiguration.objects.create(
    key="LLM_PROVIDER",
    value="openai",
    category="llm",
    is_encrypted=False
)
InstanceConfiguration.objects.create(
    key="LLM_MODEL",
    value="gpt-4o-mini",
    category="llm",
    is_encrypted=False
)

# Create setup
user = User.objects.create(email="test_llm@example.com", first_name="LLM", last_name="Test")
ws_a = Workspace.objects.create(name="LLM Test Workspace A", slug="llmtesta", owner=user)
ws_b = Workspace.objects.create(name="LLM Test Workspace B", slug="llmtestb", owner=user)
ws_c = Workspace.objects.create(name="LLM Test Workspace C", slug="llmtestc", owner=user)

print("="*60)
print("SCENARIO A: Complete Objects of the Issue section")
print("="*60)

# Create valid objects of the issue
ipo_ws_a = IPOWorkspace.objects.create(
    workspace=ws_a,
    company_name="Trinity Capital Limited",
    cin="U12345DL2026PLC123456",
    exchange_target="nse_emerge",
)
# Add promoter to shareholders list to avoid empty section warnings
ShareholderEntry.objects.create(
    ipo_workspace=ipo_ws_a,
    shareholder_name="Rajesh Gupta",
    category="promoter",
    number_of_shares=1000000,
    percentage_holding=Decimal("60.00"),
    date_of_acquisition=date(2020, 1, 1),
    acquisition_price_per_share=Decimal("10.00"),
)
ShareholderEntry.objects.create(
    ipo_workspace=ipo_ws_a,
    shareholder_name="Public Shareholder",
    category="public",
    number_of_shares=666667,
    percentage_holding=Decimal("40.00"),
    date_of_acquisition=date(2021, 1, 1),
    acquisition_price_per_share=Decimal("15.00"),
)

# Add financial summaries to avoid empty warnings
from plane.trinity.models import FinancialYearSummary
for fy, rev in [("2021-2022", "1000.00"), ("2022-2023", "1200.00"), ("2023-2024", "1500.00")]:
    FinancialYearSummary.objects.create(
        ipo_workspace=ipo_ws_a,
        financial_year=fy,
        revenue=Decimal(rev),
        ebitda=Decimal("120.00"),
        pat=Decimal("60.00"),
        net_worth=Decimal("600.00"),
    )

# Add RelatedPartyTransaction to avoid empty warnings
RelatedPartyTransaction.objects.create(
    ipo_workspace=ipo_ws_a,
    related_party_name="Gupta Packaging",
    relationship_type="entity_with_common_control",
    transaction_type="purchase",
    amount=Decimal("50.00"),
    financial_year="2023-2024",
)

ooi_a = ObjectsOfIssue.objects.create(
    ipo_workspace=ipo_ws_a,
    fresh_issue_amount=Decimal("1500.00")
)
# Add capex line item
UseOfProceeds.objects.create(
    objects_of_issue=ooi_a,
    category="capex",
    amount=Decimal("1000.00"),
    justification="Setting up a new automated manufacturing unit in Pune. The machinery includes packaging assemblies."
)
# Add general corporate purposes (exactly 10% to pass cap check)
UseOfProceeds.objects.create(
    objects_of_issue=ooi_a,
    category="general_corporate_purposes",
    amount=Decimal("150.00"),
    justification="General corporate purposes including administrative costs."
)
# Add working capital line item (already justified in layout)
UseOfProceeds.objects.create(
    objects_of_issue=ooi_a,
    category="working_capital",
    amount=Decimal("350.00"),
    justification="Financing incremental working capital requirements for purchasing raw materials."
)

try:
    draft_a = generate_draft(ipo_ws_a, "objects_of_issue")
    print(draft_a.narrative_text)
except Exception as e:
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("SCENARIO B: Objects of the Issue section with one required field empty")
print("="*60)

# Scenario B: Required field fresh_issue_amount left empty (None)
ipo_ws_b = IPOWorkspace.objects.create(
    workspace=ws_b,
    company_name="Apex Holdings Limited",
    cin="U65432DL2026PLC654321",
    exchange_target="bse_sme",
)
# Add promoter
ShareholderEntry.objects.create(
    ipo_workspace=ipo_ws_b,
    shareholder_name="Rajesh Gupta",
    category="promoter",
    number_of_shares=1000000,
    percentage_holding=Decimal("60.00"),
    date_of_acquisition=date(2020, 1, 1),
    acquisition_price_per_share=Decimal("10.00"),
)
ShareholderEntry.objects.create(
    ipo_workspace=ipo_ws_b,
    shareholder_name="Public Shareholder",
    category="public",
    number_of_shares=666667,
    percentage_holding=Decimal("40.00"),
    date_of_acquisition=date(2021, 1, 1),
    acquisition_price_per_share=Decimal("15.00"),
)

for fy, rev in [("2021-2022", "1000.00"), ("2022-2023", "1200.00"), ("2023-2024", "1500.00")]:
    FinancialYearSummary.objects.create(
        ipo_workspace=ipo_ws_b,
        financial_year=fy,
        revenue=Decimal(rev),
        ebitda=Decimal("120.00"),
        pat=Decimal("60.00"),
        net_worth=Decimal("600.00"),
    )

RelatedPartyTransaction.objects.create(
    ipo_workspace=ipo_ws_b,
    related_party_name="Gupta Packaging",
    relationship_type="entity_with_common_control",
    transaction_type="purchase",
    amount=Decimal("50.00"),
    financial_year="2023-2024",
)

ooi_b = ObjectsOfIssue.objects.create(
    ipo_workspace=ipo_ws_b,
    fresh_issue_amount=None # Deliberately empty!
)
UseOfProceeds.objects.create(
    objects_of_issue=ooi_b,
    category="capex",
    amount=Decimal("800.00"),
    justification="Purchase of robotic welding equipment."
)

try:
    draft_b = generate_draft(ipo_ws_b, "objects_of_issue")
    print(draft_b.narrative_text)
except Exception as e:
    print(f"FAILED AS EXPECTED: {e}")


print("\n" + "="*60)
print("SCENARIO C: Related Party Transactions section with name similar to but not exactly matching promoter")
print("="*60)

# Scenario C: Related Party Transactions
ipo_ws_c = IPOWorkspace.objects.create(
    workspace=ws_c,
    company_name="Apex Holdings Limited",
    cin="U65432DL2026PLC654321",
    exchange_target="bse_sme",
)
# Add promoter
ShareholderEntry.objects.create(
    ipo_workspace=ipo_ws_c,
    shareholder_name="Rajesh Gupta",
    category="promoter",
    number_of_shares=1000000,
    percentage_holding=Decimal("60.00"),
    date_of_acquisition=date(2020, 1, 1),
    acquisition_price_per_share=Decimal("10.00"),
)
ShareholderEntry.objects.create(
    ipo_workspace=ipo_ws_c,
    shareholder_name="Public Shareholder",
    category="public",
    number_of_shares=666667,
    percentage_holding=Decimal("40.00"),
    date_of_acquisition=date(2021, 1, 1),
    acquisition_price_per_share=Decimal("15.00"),
)

# Add RPTs: Rajesh Gupta Enterprise (similar name but not Rajesh Gupta exactly)
RelatedPartyTransaction.objects.create(
    ipo_workspace=ipo_ws_c,
    related_party_name="Rajesh Gupta Enterprise",
    relationship_type="entity_with_common_control",
    transaction_type="purchase of packaging materials",
    amount=Decimal("15.50"),
    financial_year="2023-2024",
    is_arms_length=True,
)

for fy, rev in [("2021-2022", "1000.00"), ("2022-2023", "1200.00"), ("2023-2024", "1500.00")]:
    FinancialYearSummary.objects.create(
        ipo_workspace=ipo_ws_c,
        financial_year=fy,
        revenue=Decimal(rev),
        ebitda=Decimal("120.00"),
        pat=Decimal("60.00"),
        net_worth=Decimal("600.00"),
    )

try:
    draft_c = generate_draft(ipo_ws_c, "related_party_transactions")
    print(draft_c.narrative_text)
except Exception as e:
    import traceback
    traceback.print_exc()

# Clean up
ws_a.delete()
ws_b.delete()
ws_c.delete()
user.delete()
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM instance_configurations WHERE key IN ('LLM_API_KEY', 'LLM_PROVIDER', 'LLM_MODEL')")
