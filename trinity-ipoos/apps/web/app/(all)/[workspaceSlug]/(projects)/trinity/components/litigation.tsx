/**
 * Trinity — Litigation & Regulatory Actions Section
 * ICDR Reference: Schedule VI, Part A, Clause 17
 */

import { useState } from "react";
import type { ILitigationEntry, IICDRSchema } from "@/services/trinity.service";
import { TrinityService } from "@/services/trinity.service";
import { ICDRClauseTag } from "./icdr-clause-tag";

const trinityService = new TrinityService();

interface Props {
  workspaceSlug: string;
  data: ILitigationEntry[];
  schema?: IICDRSchema;
  onDataChange: (data: ILitigationEntry[]) => void;
  showSaveMessage: (msg: string) => void;
}

const CASE_TYPE_OPTIONS = [
  { value: "criminal", label: "Criminal Proceedings" },
  { value: "civil", label: "Civil Litigation" },
  { value: "regulatory", label: "Regulatory Actions" },
  { value: "tax", label: "Tax Proceedings" },
];

const empty = (): Partial<ILitigationEntry> => ({
  case_type: "civil", party_involved: "", court_or_authority: "", status: "", amount_involved: null,
});

export function LitigationSection({ workspaceSlug, data, schema, onDataChange, showSaveMessage }: Props) {
  const [editItem, setEditItem] = useState<Partial<ILitigationEntry> | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [saving, setSaving] = useState(false);

  const startAdd = () => { setEditItem(empty()); setIsNew(true); };
  const startEdit = (item: ILitigationEntry) => { setEditItem({ ...item }); setIsNew(false); };
  const cancelEdit = () => { setEditItem(null); setIsNew(false); };

  const saveItem = async () => {
    if (!editItem) return;
    setSaving(true);
    try {
      if (isNew) {
        const created = await trinityService.createLitigation(workspaceSlug, editItem);
        onDataChange([...data, created]);
        showSaveMessage("Case added");
      } else {
        const updated = await trinityService.updateLitigation(workspaceSlug, editItem.id!, editItem);
        onDataChange(data.map((d) => (d.id === updated.id ? updated : d)));
        showSaveMessage("Case updated");
      }
      cancelEdit();
    } catch (err) { console.error(err); } finally { setSaving(false); }
  };

  const deleteItem = async (id: string) => {
    await trinityService.deleteLitigation(workspaceSlug, id);
    onDataChange(data.filter((d) => d.id !== id));
    showSaveMessage("Case removed");
  };

  const caseTypeIcon = (t: string) => ({ criminal: "🔴", civil: "🟡", regulatory: "🟠", tax: "🔵" }[t] || "⚪");

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-custom-text-100">Litigation & Regulatory Actions</h2>
        <p className="mt-1 text-sm text-custom-text-300">All pending litigation, regulatory actions, and legal proceedings.</p>
        {schema && <ICDRClauseTag clause={schema.regulation_reference} />}
      </div>

      {data.length === 0 && !editItem && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950/30">
          <p className="text-sm text-green-700 dark:text-green-400">
            No litigation entries yet. If there are no pending cases, you may proceed to the next section.
            However, note that this section must still be disclosed in the DRHP (as "nil").
          </p>
        </div>
      )}

      {data.map((item) => (
        <div key={item.id} className="mb-2 flex items-center justify-between rounded-lg border border-custom-border-200 bg-custom-background-90 px-4 py-3">
          <div>
            <div className="flex items-center gap-2">
              <span>{caseTypeIcon(item.case_type)}</span>
              <span className="text-sm font-medium text-custom-text-100">{item.party_involved}</span>
              <span className="rounded-full bg-custom-background-80 px-2 py-0.5 text-[10px] font-medium text-custom-text-300">
                {CASE_TYPE_OPTIONS.find((o) => o.value === item.case_type)?.label}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-custom-text-300">
              {item.court_or_authority} • {item.status}
              {item.amount_involved ? ` • ₹${item.amount_involved}L` : ""}
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => startEdit(item)} className="rounded px-2 py-1 text-xs text-custom-text-300 hover:bg-custom-background-80">Edit</button>
            <button onClick={() => deleteItem(item.id!)} className="rounded px-2 py-1 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30">Delete</button>
          </div>
        </div>
      ))}

      {editItem ? (
        <div className="mt-2 rounded-lg border border-custom-primary-100/30 bg-custom-background-90 p-5">
          <h3 className="mb-4 text-sm font-semibold text-custom-text-200">{isNew ? "Add" : "Edit"} Case</h3>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Case Type *</label>
              <select value={editItem.case_type||"civil"} onChange={(e)=>setEditItem(p=>({...p!,case_type:e.target.value as any}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none">
                {CASE_TYPE_OPTIONS.map(o=>(<option key={o.value} value={o.value}>{o.label}</option>))}</select></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Amount Involved (₹ Lakhs)</label>
              <input type="number" step="0.01" value={editItem.amount_involved||""} onChange={(e)=>setEditItem(p=>({...p!,amount_involved:e.target.value||null}))} placeholder="Optional" className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div className="col-span-2"><label className="mb-1 block text-xs font-medium text-custom-text-300">Party Involved *</label>
              <input type="text" value={editItem.party_involved||""} onChange={(e)=>setEditItem(p=>({...p!,party_involved:e.target.value}))} placeholder="e.g., Company vs. Tax Authority" className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div className="col-span-2"><label className="mb-1 block text-xs font-medium text-custom-text-300">Court / Authority *</label>
              <input type="text" value={editItem.court_or_authority||""} onChange={(e)=>setEditItem(p=>({...p!,court_or_authority:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div className="col-span-2"><label className="mb-1 block text-xs font-medium text-custom-text-300">Current Status *</label>
              <textarea rows={2} value={editItem.status||""} onChange={(e)=>setEditItem(p=>({...p!,status:e.target.value}))} placeholder="e.g., Pending hearing, next date 15-Aug-2026" className="w-full resize-none rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none"/></div>
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={saveItem} disabled={saving} className="rounded-lg bg-custom-primary-100 px-4 py-2 text-sm font-medium text-white hover:bg-custom-primary-200 disabled:opacity-50">{saving?"Saving…":isNew?"Add Case":"Update Case"}</button>
            <button onClick={cancelEdit} className="rounded-lg border border-custom-border-200 px-4 py-2 text-sm font-medium text-custom-text-200 hover:bg-custom-background-80">Cancel</button>
          </div>
        </div>
      ) : (
        <button onClick={startAdd} className="mt-2 w-full rounded-lg border-2 border-dashed border-custom-border-200 px-4 py-6 text-sm text-custom-text-300 hover:border-custom-primary-100 hover:text-custom-primary-100">+ Add Litigation / Regulatory Case</button>
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
