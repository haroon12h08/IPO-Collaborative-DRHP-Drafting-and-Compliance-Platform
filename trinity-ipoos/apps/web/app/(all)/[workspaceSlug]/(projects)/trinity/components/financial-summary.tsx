/**
 * Trinity — Financial Summary Section (Last 3 FYs)
 * ICDR Reference: Schedule VI, Part A, Clause 10
 */

import { useState } from "react";
import type { IFinancialYearSummary, IICDRSchema } from "@/services/trinity.service";
import { TrinityService } from "@/services/trinity.service";
import { ICDRClauseTag } from "./icdr-clause-tag";

const trinityService = new TrinityService();

interface Props {
  workspaceSlug: string;
  data: IFinancialYearSummary[];
  schema?: IICDRSchema;
  onDataChange: (data: IFinancialYearSummary[]) => void;
  showSaveMessage: (msg: string) => void;
}

const empty = (): Partial<IFinancialYearSummary> => ({
  financial_year: "", revenue: "", ebitda: "", pat: "", net_worth: "",
});

export function FinancialSummarySection({ workspaceSlug, data, schema, onDataChange, showSaveMessage }: Props) {
  const [editItem, setEditItem] = useState<Partial<IFinancialYearSummary> | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [saving, setSaving] = useState(false);

  const startAdd = () => { setEditItem(empty()); setIsNew(true); };
  const startEdit = (item: IFinancialYearSummary) => { setEditItem({ ...item }); setIsNew(false); };
  const cancelEdit = () => { setEditItem(null); setIsNew(false); };

  const saveItem = async () => {
    if (!editItem) return;
    setSaving(true);
    try {
      if (isNew) {
        const created = await trinityService.createFinancial(workspaceSlug, editItem);
        onDataChange([...data, created]);
        showSaveMessage("Financial year added");
      } else {
        const updated = await trinityService.updateFinancial(workspaceSlug, editItem.id!, editItem);
        onDataChange(data.map((d) => (d.id === updated.id ? updated : d)));
        showSaveMessage("Financial year updated");
      }
      cancelEdit();
    } catch (err) { console.error(err); } finally { setSaving(false); }
  };

  const deleteItem = async (id: string) => {
    await trinityService.deleteFinancial(workspaceSlug, id);
    onDataChange(data.filter((d) => d.id !== id));
    showSaveMessage("Financial year removed");
  };

  // Check EBITDA positivity (2 out of 3 years required)
  const ebitdaPositiveYears = data.filter((d) => parseFloat(d.ebitda) > 0).length;
  const hasMinNetWorth = data.some((d) => parseFloat(d.net_worth) >= 100); // ₹1Cr = 100L

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-custom-text-100">Financial Summary</h2>
        <p className="mt-1 text-sm text-custom-text-300">
          Basic financial figures for the last 3 financial years. Enter once — referenced by other sections.
        </p>
        {schema && <ICDRClauseTag clause={schema.regulation_reference} />}
      </div>

      {/* Eligibility Checks */}
      {data.length > 0 && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div className={`rounded-lg border p-3 ${ebitdaPositiveYears >= 2
            ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30"
            : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30"}`}>
            <p className={`text-sm font-medium ${ebitdaPositiveYears >= 2 ? "text-green-700 dark:text-green-400" : "text-red-700 dark:text-red-400"}`}>
              {ebitdaPositiveYears >= 2 ? "✓" : "✗"} EBITDA positive: {ebitdaPositiveYears}/3 years
            </p>
            <p className="mt-0.5 text-xs text-custom-text-400">Reg 229(2)(d): Need ≥2 out of 3</p>
          </div>
          <div className={`rounded-lg border p-3 ${hasMinNetWorth
            ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30"
            : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30"}`}>
            <p className={`text-sm font-medium ${hasMinNetWorth ? "text-green-700 dark:text-green-400" : "text-red-700 dark:text-red-400"}`}>
              {hasMinNetWorth ? "✓" : "✗"} Net Worth ≥ ₹1 Crore
            </p>
            <p className="mt-0.5 text-xs text-custom-text-400">Reg 229(2)(b): Minimum net worth</p>
          </div>
        </div>
      )}

      {/* Financial Year Table */}
      {data.length > 0 && (
        <div className="mb-4 overflow-hidden rounded-lg border border-custom-border-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-custom-border-200 bg-custom-background-90">
                <th className="px-4 py-2 text-left text-xs font-semibold text-custom-text-300">FY</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-custom-text-300">Revenue</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-custom-text-300">EBITDA</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-custom-text-300">PAT</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-custom-text-300">Net Worth</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-custom-text-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.id} className="border-b border-custom-border-100 last:border-0">
                  <td className="px-4 py-2 font-medium text-custom-text-100">{item.financial_year}</td>
                  <td className="px-4 py-2 text-right text-custom-text-200">₹{parseFloat(item.revenue).toFixed(2)}L</td>
                  <td className={`px-4 py-2 text-right ${parseFloat(item.ebitda) > 0 ? "text-green-600" : "text-red-500"}`}>
                    ₹{parseFloat(item.ebitda).toFixed(2)}L
                  </td>
                  <td className={`px-4 py-2 text-right ${parseFloat(item.pat) > 0 ? "text-green-600" : "text-red-500"}`}>
                    ₹{parseFloat(item.pat).toFixed(2)}L
                  </td>
                  <td className="px-4 py-2 text-right text-custom-text-200">₹{parseFloat(item.net_worth).toFixed(2)}L</td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => startEdit(item)} className="mr-2 text-xs text-custom-text-300 hover:text-custom-text-100">Edit</button>
                    <button onClick={() => deleteItem(item.id!)} className="text-xs text-red-500 hover:text-red-600">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editItem ? (
        <div className="rounded-lg border border-custom-primary-100/30 bg-custom-background-90 p-5">
          <h3 className="mb-4 text-sm font-semibold text-custom-text-200">{isNew ? "Add" : "Edit"} Financial Year</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2"><label className="mb-1 block text-xs font-medium text-custom-text-300">Financial Year *</label>
              <input type="text" maxLength={9} value={editItem.financial_year||""} onChange={(e)=>setEditItem(p=>({...p!,financial_year:e.target.value}))} placeholder="2023-2024" className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Revenue (₹ Lakhs) *</label>
              <input type="number" step="0.01" value={editItem.revenue||""} onChange={(e)=>setEditItem(p=>({...p!,revenue:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">EBITDA (₹ Lakhs) *</label>
              <input type="number" step="0.01" value={editItem.ebitda||""} onChange={(e)=>setEditItem(p=>({...p!,ebitda:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">PAT (₹ Lakhs) *</label>
              <input type="number" step="0.01" value={editItem.pat||""} onChange={(e)=>setEditItem(p=>({...p!,pat:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Net Worth (₹ Lakhs) *</label>
              <input type="number" step="0.01" value={editItem.net_worth||""} onChange={(e)=>setEditItem(p=>({...p!,net_worth:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={saveItem} disabled={saving} className="rounded-lg bg-custom-primary-100 px-4 py-2 text-sm font-medium text-white hover:bg-custom-primary-200 disabled:opacity-50">{saving?"Saving…":isNew?"Add":"Update"}</button>
            <button onClick={cancelEdit} className="rounded-lg border border-custom-border-200 px-4 py-2 text-sm font-medium text-custom-text-200 hover:bg-custom-background-80">Cancel</button>
          </div>
        </div>
      ) : data.length < 3 ? (
        <button onClick={startAdd} className="w-full rounded-lg border-2 border-dashed border-custom-border-200 px-4 py-6 text-sm text-custom-text-300 hover:border-custom-primary-100 hover:text-custom-primary-100">
          + Add Financial Year ({3 - data.length} remaining)
        </button>
      ) : (
        <p className="text-center text-sm text-custom-text-400">All 3 financial years entered ✓</p>
      )}

      {schema?.notes && (
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <h4 className="mb-2 text-xs font-semibold uppercase text-amber-800 dark:text-amber-300">Regulatory Notes</h4>
          <ul className="space-y-1">{schema.notes.map((n,i)=>(<li key={i} className="text-xs text-amber-700 dark:text-amber-400">• {n}</li>))}</ul>
        </div>
      )}
    </div>
  );
}
