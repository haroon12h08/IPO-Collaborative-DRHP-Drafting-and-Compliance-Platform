/**
 * Trinity IPO Preparation Tool — API Service
 *
 * Follows Plane's existing service pattern (extends APIService).
 * All endpoints are workspace-scoped via the slug parameter.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface IIPOWorkspace {
  id: string;
  exists?: boolean;
  company_name: string;
  cin?: string;
  exchange_target: "nse_emerge" | "bse_sme";
  status: "draft" | "review" | "submitted";
  sections_status?: Record<string, boolean>;
  workspace: string;
  created_at?: string;
  updated_at?: string;
}

export interface IUseOfProceeds {
  id?: string;
  category: "capex" | "working_capital" | "general_corporate_purposes" | "debt_repayment" | "other";
  amount: string; // decimal as string
  justification: string;
  repayment_counterparty_id?: string;
  sort_order?: number;
}

export interface IObjectsOfIssue {
  id?: string;
  exists?: boolean;
  fresh_issue_amount?: string;
  use_of_proceeds: IUseOfProceeds[];
}

export interface IRelatedPartyTransaction {
  id?: string;
  related_party_name: string;
  relationship_type: string;
  transaction_type: string;
  amount: string;
  financial_year: string;
  is_arms_length: boolean;
}

export interface IShareholderEntry {
  id?: string;
  shareholder_name: string;
  category: "promoter" | "promoter_group" | "public";
  number_of_shares: number;
  percentage_holding: string;
  date_of_acquisition: string;
  acquisition_price_per_share: string;
}

export interface ILitigationEntry {
  id?: string;
  case_type: "criminal" | "civil" | "regulatory" | "tax";
  party_involved: string;
  court_or_authority: string;
  status: string;
  amount_involved?: string | null;
}

export interface IFinancialYearSummary {
  id?: string;
  financial_year: string;
  revenue: string;
  ebitda: string;
  pat: string;
  net_worth: string;
}

export interface IICDRSchema {
  section_id: string;
  section_title: string;
  regulation_reference: string;
  description: string;
  fields: Record<string, IICDRFieldSchema>;
  line_item_fields?: Record<string, IICDRFieldSchema>;
  notes: string[];
}

export interface IICDRFieldSchema {
  label: string;
  type: string;
  required: boolean;
  icdr_clause: string;
  icdr_text: string;
  help_text: string;
  choices?: string[];
  choice_labels?: Record<string, string>;
  max_length?: number;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export class TrinityService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  // ICDR Schemas
  async fetchAllSchemas(workspaceSlug: string): Promise<Record<string, IICDRSchema>> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/schemas/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async fetchSchema(workspaceSlug: string, sectionId: string): Promise<IICDRSchema> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/schemas/${sectionId}/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  // IPO Workspace
  async fetchIPOWorkspace(workspaceSlug: string): Promise<IIPOWorkspace> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async createIPOWorkspace(workspaceSlug: string, data: Partial<IIPOWorkspace>): Promise<IIPOWorkspace> {
    return this.post(`/api/trinity/workspaces/${workspaceSlug}/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async updateIPOWorkspace(workspaceSlug: string, data: Partial<IIPOWorkspace>): Promise<IIPOWorkspace> {
    return this.patch(`/api/trinity/workspaces/${workspaceSlug}/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  // Section 1 — Objects of the Issue
  async fetchObjectsOfIssue(workspaceSlug: string): Promise<IObjectsOfIssue> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/objects-of-issue/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async saveObjectsOfIssue(workspaceSlug: string, data: Partial<IObjectsOfIssue>): Promise<IObjectsOfIssue> {
    return this.post(`/api/trinity/workspaces/${workspaceSlug}/objects-of-issue/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  // Section 2 — Related Party Transactions
  async fetchRPTs(workspaceSlug: string): Promise<IRelatedPartyTransaction[]> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/related-party-transactions/`)
      .then((r) => r?.data?.results ?? r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async createRPT(workspaceSlug: string, data: Partial<IRelatedPartyTransaction>): Promise<IRelatedPartyTransaction> {
    return this.post(`/api/trinity/workspaces/${workspaceSlug}/related-party-transactions/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async updateRPT(workspaceSlug: string, id: string, data: Partial<IRelatedPartyTransaction>): Promise<IRelatedPartyTransaction> {
    return this.patch(`/api/trinity/workspaces/${workspaceSlug}/related-party-transactions/${id}/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async deleteRPT(workspaceSlug: string, id: string): Promise<void> {
    return this.delete(`/api/trinity/workspaces/${workspaceSlug}/related-party-transactions/${id}/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  // Section 3 — Shareholders
  async fetchShareholders(workspaceSlug: string): Promise<IShareholderEntry[]> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/shareholders/`)
      .then((r) => r?.data?.results ?? r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async createShareholder(workspaceSlug: string, data: Partial<IShareholderEntry>): Promise<IShareholderEntry> {
    return this.post(`/api/trinity/workspaces/${workspaceSlug}/shareholders/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async updateShareholder(workspaceSlug: string, id: string, data: Partial<IShareholderEntry>): Promise<IShareholderEntry> {
    return this.patch(`/api/trinity/workspaces/${workspaceSlug}/shareholders/${id}/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async deleteShareholder(workspaceSlug: string, id: string): Promise<void> {
    return this.delete(`/api/trinity/workspaces/${workspaceSlug}/shareholders/${id}/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  // Section 4 — Litigation
  async fetchLitigations(workspaceSlug: string): Promise<ILitigationEntry[]> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/litigations/`)
      .then((r) => r?.data?.results ?? r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async createLitigation(workspaceSlug: string, data: Partial<ILitigationEntry>): Promise<ILitigationEntry> {
    return this.post(`/api/trinity/workspaces/${workspaceSlug}/litigations/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async updateLitigation(workspaceSlug: string, id: string, data: Partial<ILitigationEntry>): Promise<ILitigationEntry> {
    return this.patch(`/api/trinity/workspaces/${workspaceSlug}/litigations/${id}/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async deleteLitigation(workspaceSlug: string, id: string): Promise<void> {
    return this.delete(`/api/trinity/workspaces/${workspaceSlug}/litigations/${id}/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  // Section 5 — Financial Summary
  async fetchFinancials(workspaceSlug: string): Promise<IFinancialYearSummary[]> {
    return this.get(`/api/trinity/workspaces/${workspaceSlug}/financials/`)
      .then((r) => r?.data?.results ?? r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async createFinancial(workspaceSlug: string, data: Partial<IFinancialYearSummary>): Promise<IFinancialYearSummary> {
    return this.post(`/api/trinity/workspaces/${workspaceSlug}/financials/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async updateFinancial(workspaceSlug: string, id: string, data: Partial<IFinancialYearSummary>): Promise<IFinancialYearSummary> {
    return this.patch(`/api/trinity/workspaces/${workspaceSlug}/financials/${id}/`, data)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }

  async deleteFinancial(workspaceSlug: string, id: string): Promise<void> {
    return this.delete(`/api/trinity/workspaces/${workspaceSlug}/financials/${id}/`)
      .then((r) => r?.data)
      .catch((e) => { throw e?.response?.data; });
  }
}
