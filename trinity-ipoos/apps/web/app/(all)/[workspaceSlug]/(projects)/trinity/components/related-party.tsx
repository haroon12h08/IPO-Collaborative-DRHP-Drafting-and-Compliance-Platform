/**
 * Trinity — Related Party Transactions Section
 * ICDR Reference: Schedule VI, Part A, Clause 14
 *
 * CRUD list with inline add/edit and per-record save.
 */

import { useState } from "react";
import type { IRelatedPartyTransaction, IICDRSchema } from "@/services/trinity.service";
import { TrinityService } from "@/services/trinity.service";
import { ICDRClauseTag } from "./icdr-clause-tag";

const trinityService = new TrinityService();

interface Props {
  workspaceSlug: string;
  data: IRelatedPartyTransaction[];
  schema?: IICDRSchema;
  onDataChange: (data: IRelatedPartyTransaction[]) => void;
  showSaveMessage: (msg: string) => void;
}

const RELATIONSHIP_OPTIONS = [
  { value: "promoter", label: "Promoter" },
  { value: "promoter_group", label: "Promoter Group Entity" },
  { value: "director", label: "Director" },
  { value: "key_management_personnel", label: "Key Management Personnel" },
  { value: "subsidiary", label: "Subsidiary Company" },
  { value: "associate", label: "Associate Company" },
  { value: "joint_venture", label: "Joint Venture" },
  { value: "relative_of_director", label: "Relative of Director/KMP" },
  { value: "entity_with_common_control", label: "Entity under Common Control" },
  { value: "other", label: "Other Related Party" },
];

const emptyRPT = (): Partial<IRelatedPartyTransaction> => ({
  related_party_name: "",
  relationship_type: "promoter",
  transaction_type: "",
  amount: "",
  financial_year: "",
  is_arms_length: true,
});

export function RelatedPartySection({ workspaceSlug, data, schema, onDataChange, showSaveMessage }: Props) {
  const [editItem, setEditItem] = useState<Partial<IRelatedPartyTransaction> | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [saving, setSaving] = useState(false);

  const startAdd = () => {
    setEditItem(emptyRPT());
    setIsNew(true);
  };

  const startEdit = (item: IRelatedPartyTransaction) => {
    setEditItem({ ...item });
    setIsNew(false);
  };

  const cancelEdit = () => {
    setEditItem(null);
    setIsNew(false);
  };

  const saveItem = async () => {
    if (!editItem) return;
    setSaving(true);
    try {
      if (isNew) {
        const created = await trinityService.createRPT(workspaceSlug, editItem);
        onDataChange([...data, created]);
        showSaveMessage("Transaction added");
      } else {
        const updated = await trinityService.updateRPT(workspaceSlug, editItem.id!, editItem);
        onDataChange(data.map((d) => (d.id === updated.id ? updated : d)));
        showSaveMessage("Transaction updated");
      }
      setEditItem(null);
      setIsNew(false);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const deleteItem = async (id: string) => {
    try {
      await trinityService.deleteRPT(workspaceSlug, id);
      onDataChange(data.filter((d) => d.id !== id));
      showSaveMessage("Transaction removed");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-custom-text-100">Related Party Transactions</h2>
        <p className="mt-1 text-sm text-custom-text-300">
          Disclose all material transactions with related parties for the last 3 financial years.
        </p>
        {schema && <ICDRClauseTag clause={schema.regulation_reference} />}
      </div>

      {/* Existing Records */}
      {data.length > 0 && (
        <div className="mb-4 space-y-2">
          {data.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded-lg border border-custom-border-200 bg-custom-background-90 px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-custom-text-100">{item.related_party_name}</span>
                  <span className="rounded-full bg-custom-primary-100/10 px-2 py-0.5 text-[10px] font-medium text-custom-primary-100">
                    {RELATIONSHIP_OPTIONS.find((o) => o.value === item.relationship_type)?.label}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-custom-text-300">
                  {item.transaction_type} • ₹{item.amount}L • FY {item.financial_year} •{" "}
                  {item.is_arms_length ? "Arm's length ✓" : "Not arm's length ✗"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => startEdit(item)}
                  className="rounded px-2 py-1 text-xs text-custom-text-300 hover:bg-custom-background-80 hover:text-custom-text-100"
                >
                  Edit
                </button>
                <button
                  onClick={() => deleteItem(item.id!)}
                  className="rounded px-2 py-1 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Form */}
      {editItem ? (
        <div className="rounded-lg border border-custom-primary-100/30 bg-custom-background-90 p-5">
          <h3 className="mb-4 text-sm font-semibold text-custom-text-200">
            {isNew ? "Add Transaction" : "Edit Transaction"}
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-custom-text-300">Related Party Name *</label>
              <input
                type="text"
                value={editItem.related_party_name || ""}
                onChange={(e) => setEditItem((p) => ({ ...p!, related_party_name: e.target.value }))}
                className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-custom-text-300">Relationship Type *</label>
              <select
                value={editItem.relationship_type || "promoter"}
                onChange={(e) => setEditItem((p) => ({ ...p!, relationship_type: e.target.value }))}
                className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"
              >
                {RELATIONSHIP_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-custom-text-300">Transaction Type *</label>
              <input
                type="text"
                value={editItem.transaction_type || ""}
                onChange={(e) => setEditItem((p) => ({ ...p!, transaction_type: e.target.value }))}
                placeholder="e.g., Sale of goods, Rent paid"
                className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-custom-text-300">Amount (₹ Lakhs) *</label>
              <input
                type="number"
                step="0.01"
                value={editItem.amount || ""}
                onChange={(e) => setEditItem((p) => ({ ...p!, amount: e.target.value }))}
                className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-custom-text-300">Financial Year *</label>
              <input
                type="text"
                value={editItem.financial_year || ""}
                onChange={(e) => setEditItem((p) => ({ ...p!, financial_year: e.target.value }))}
                placeholder="2023-2024"
                maxLength={9}
                className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm text-custom-text-200">
                <input
                  type="checkbox"
                  checked={editItem.is_arms_length ?? true}
                  onChange={(e) => setEditItem((p) => ({ ...p!, is_arms_length: e.target.checked }))}
                  className="h-4 w-4 rounded border-custom-border-200 text-custom-primary-100 focus:ring-custom-primary-100"
                />
                At Arm's Length
              </label>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={saveItem}
              disabled={saving}
              className="rounded-lg bg-custom-primary-100 px-4 py-2 text-sm font-medium text-white transition hover:bg-custom-primary-200 disabled:opacity-50"
            >
              {saving ? "Saving…" : isNew ? "Add Transaction" : "Update Transaction"}
            </button>
            <button
              onClick={cancelEdit}
              className="rounded-lg border border-custom-border-200 px-4 py-2 text-sm font-medium text-custom-text-200 transition hover:bg-custom-background-80"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={startAdd}
          className="w-full rounded-lg border-2 border-dashed border-custom-border-200 px-4 py-6 text-sm text-custom-text-300 transition hover:border-custom-primary-100 hover:text-custom-primary-100"
        >
          + Add Related Party Transaction
        </button>
      )}

      {/* Schema Notes */}
      {schema?.notes && (
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <h4 className="mb-2 text-xs font-semibold uppercase text-amber-800 dark:text-amber-300">Regulatory Notes</h4>
          <ul className="space-y-1">
            {schema.notes.map((note, i) => (
              <li key={i} className="text-xs text-amber-700 dark:text-amber-400">• {note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
