/**
 * Trinity — Objects of the Issue Section
 * ICDR Reference: Schedule VI, Part A, Clause 2(1)
 *
 * Handles the fresh issue amount and use-of-proceeds line items.
 */

import { useState, useEffect } from "react";
import type { IObjectsOfIssue, IUseOfProceeds, IICDRSchema, IRelatedPartyTransaction, IShareholderEntry } from "@/services/trinity.service";
import { ICDRClauseTag } from "./icdr-clause-tag";

interface Props {
  workspaceSlug: string;
  data: IObjectsOfIssue | null;
  schema?: IICDRSchema;
  onSave: (data: Partial<IObjectsOfIssue>) => Promise<void>;
  saving: boolean;
  rpts?: IRelatedPartyTransaction[];
  shareholders?: IShareholderEntry[];
}

const CATEGORY_OPTIONS = [
  { value: "capex", label: "Capital Expenditure" },
  { value: "working_capital", label: "Working Capital" },
  { value: "general_corporate_purposes", label: "General Corporate Purposes" },
  { value: "debt_repayment", label: "Debt Repayment" },
  { value: "other", label: "Other" },
];

const emptyLineItem = (): IUseOfProceeds => ({
  category: "capex",
  amount: "",
  justification: "",
  repayment_counterparty_id: "",
});

export function ObjectsOfIssueSection({ workspaceSlug, data, schema, onSave, saving, rpts = [], shareholders = [] }: Props) {
  const [freshIssueAmount, setFreshIssueAmount] = useState("");
  const [lineItems, setLineItems] = useState<IUseOfProceeds[]>([emptyLineItem()]);

  useEffect(() => {
    if (data) {
      setFreshIssueAmount(data.fresh_issue_amount || "");
      if (data.use_of_proceeds?.length) {
        setLineItems(data.use_of_proceeds);
      }
    }
  }, [data]);

  const addLineItem = () => setLineItems((prev) => [...prev, emptyLineItem()]);

  const removeLineItem = (idx: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateLineItem = (idx: number, field: keyof IUseOfProceeds, value: string) => {
    setLineItems((prev) =>
      prev.map((item, i) => {
        if (i === idx) {
          const updated = { ...item, [field]: value };
          if (field === "category" && value !== "debt_repayment") {
            updated.repayment_counterparty_id = "";
          }
          return updated;
        }
        return item;
      })
    );
  };

  const totalProceeds = lineItems.reduce(
    (sum, item) => sum + (parseFloat(item.amount) || 0),
    0
  );

  const handleSave = () => {
    for (let i = 0; i < lineItems.length; i++) {
      const item = lineItems[i];
      if (item.category === "debt_repayment" && !item.repayment_counterparty_id) {
        alert(`Line Item #${i + 1} (Debt Repayment) is missing a repayment counterparty. Please select a promoter shareholder or related party from the dropdown.`);
        return;
      }
    }
    onSave({
      fresh_issue_amount: freshIssueAmount,
      use_of_proceeds: lineItems.filter((item) => item.amount && item.justification),
    });
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-custom-text-100">Objects of the Issue</h2>
        <p className="mt-1 text-sm text-custom-text-300">
          Specify the purpose for which funds are being raised and the detailed use of proceeds.
        </p>
        {schema && (
          <ICDRClauseTag clause={schema.regulation_reference} />
        )}
      </div>

      {/* Fresh Issue Amount */}
      <div className="mb-6">
        <label htmlFor="fresh_issue_amount" className="mb-1.5 block text-sm font-medium text-custom-text-200">
          Fresh Issue Amount (₹ in Lakhs) <span className="text-red-500">*</span>
        </label>
        {schema?.fields?.fresh_issue_amount && (
          <ICDRClauseTag
            clause={schema.fields.fresh_issue_amount.icdr_clause}
            text={schema.fields.fresh_issue_amount.icdr_text}
          />
        )}
        <input
          id="fresh_issue_amount"
          type="number"
          step="0.01"
          min="0"
          value={freshIssueAmount}
          onChange={(e) => setFreshIssueAmount(e.target.value)}
          placeholder="e.g., 5000.00"
          className="mt-2 w-full rounded-lg border border-custom-border-200 bg-custom-background-100 px-3 py-2 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none focus:ring-1 focus:ring-custom-primary-100"
        />
      </div>

      {/* Use of Proceeds Line Items */}
      <div className="mb-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-custom-text-200">Use of Proceeds Breakdown</h3>
          <button
            onClick={addLineItem}
            className="rounded-md bg-custom-primary-100/10 px-3 py-1 text-xs font-medium text-custom-primary-100 transition hover:bg-custom-primary-100/20"
          >
            + Add Line Item
          </button>
        </div>

        <div className="space-y-4">
          {lineItems.map((item, idx) => (
            <div
              key={idx}
              className="rounded-lg border border-custom-border-200 bg-custom-background-90 p-4"
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-medium text-custom-text-400">
                  Line Item #{idx + 1}
                </span>
                {lineItems.length > 1 && (
                  <button
                    onClick={() => removeLineItem(idx)}
                    className="text-xs text-red-500 hover:text-red-600"
                  >
                    Remove
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-xs font-medium text-custom-text-300">
                    Category
                  </label>
                  <select
                    value={item.category}
                    onChange={(e) => updateLineItem(idx, "category", e.target.value)}
                    className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"
                  >
                    {CATEGORY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-custom-text-300">
                    Amount (₹ Lakhs)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={item.amount}
                    onChange={(e) => updateLineItem(idx, "amount", e.target.value)}
                    placeholder="0.00"
                    className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"
                  />
                </div>
              </div>
              <div className="mt-3">
                <label className="mb-1 block text-xs font-medium text-custom-text-300">
                  Justification / Rationale
                </label>
                <textarea
                  rows={3}
                  value={item.justification}
                  onChange={(e) => updateLineItem(idx, "justification", e.target.value)}
                  placeholder="Provide a detailed rationale for this specific use of funds…"
                  className="w-full resize-none rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"
                />
              </div>
              {item.category === "debt_repayment" && (
                <div className="mt-3">
                  <label className="mb-1 block text-xs font-medium text-custom-text-300">
                    Repayment Counterparty <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={item.repayment_counterparty_id || ""}
                    onChange={(e) => updateLineItem(idx, "repayment_counterparty_id", e.target.value)}
                    className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"
                  >
                    <option value="">-- Select Shareholder or Related Party --</option>
                    <optgroup label="Promoters / Promoter Group (Shareholders)">
                      {shareholders
                        ?.filter((sh) => sh.category === "promoter" || sh.category === "promoter_group")
                        .map((sh) => (
                          <option key={sh.id} value={sh.id}>
                            {sh.shareholder_name} ({sh.category === "promoter" ? "Promoter" : "Promoter Group"})
                          </option>
                        ))}
                    </optgroup>
                    <optgroup label="Other Related Parties (Transactions)">
                      {rpts
                        ?.filter((rpt) => rpt.relationship_type === "promoter" || rpt.relationship_type === "promoter_group")
                        .map((rpt) => (
                          <option key={rpt.id} value={rpt.id}>
                            {rpt.related_party_name} ({rpt.relationship_type === "promoter" ? "Promoter" : "Promoter Group Entity"})
                          </option>
                        ))}
                    </optgroup>
                    <optgroup label="Non-Promoters (For Reference)">
                      {shareholders
                        ?.filter((sh) => sh.category !== "promoter" && sh.category !== "promoter_group")
                        .map((sh) => (
                          <option key={sh.id} value={sh.id}>
                            {sh.shareholder_name} (Public Shareholder)
                          </option>
                        ))}
                      {rpts
                        ?.filter((rpt) => rpt.relationship_type !== "promoter" && rpt.relationship_type !== "promoter_group")
                        .map((rpt) => (
                          <option key={rpt.id} value={rpt.id}>
                            {rpt.related_party_name} (Related Party - {rpt.relationship_type})
                          </option>
                        ))}
                    </optgroup>
                  </select>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="mb-6 rounded-lg border border-custom-border-200 bg-custom-background-90 p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-custom-text-200">Total Proceeds Allocated</span>
          <span className="text-sm font-semibold text-custom-text-100">
            ₹ {totalProceeds.toFixed(2)} Lakhs
          </span>
        </div>
        {freshIssueAmount && totalProceeds !== parseFloat(freshIssueAmount) && (
          <p className="mt-2 text-xs text-amber-600">
            ⚠ Total proceeds (₹{totalProceeds.toFixed(2)}L) do not match the fresh issue amount
            (₹{parseFloat(freshIssueAmount).toFixed(2)}L)
          </p>
        )}
      </div>

      {/* Schema Notes */}
      {schema?.notes && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <h4 className="mb-2 text-xs font-semibold uppercase text-amber-800 dark:text-amber-300">
            Regulatory Notes
          </h4>
          <ul className="space-y-1">
            {schema.notes.map((note, i) => (
              <li key={i} className="text-xs text-amber-700 dark:text-amber-400">
                • {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        className="rounded-lg bg-custom-primary-100 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-custom-primary-200 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save Objects of the Issue"}
      </button>
    </div>
  );
}
