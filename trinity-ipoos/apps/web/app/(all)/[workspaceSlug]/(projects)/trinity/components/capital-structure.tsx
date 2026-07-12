/**
 * Trinity — Capital Structure / Promoter Shareholding Section
 * ICDR Reference: Schedule VI, Part A, Clauses 4 & 5
 */

import { useState } from "react";
import type { IShareholderEntry, IICDRSchema } from "@/services/trinity.service";
import { TrinityService } from "@/services/trinity.service";
import { ICDRClauseTag } from "./icdr-clause-tag";

const trinityService = new TrinityService();

interface Props {
  workspaceSlug: string;
  data: IShareholderEntry[];
  schema?: IICDRSchema;
  onDataChange: (data: IShareholderEntry[]) => void;
  showSaveMessage: (msg: string) => void;
}

const CATEGORY_OPTIONS = [
  { value: "promoter", label: "Promoter" },
  { value: "promoter_group", label: "Promoter Group" },
  { value: "public", label: "Public Shareholder" },
];

const empty = (): Partial<IShareholderEntry> => ({
  shareholder_name: "", category: "promoter", number_of_shares: 0,
  percentage_holding: "", date_of_acquisition: "", acquisition_price_per_share: "",
});

export function CapitalStructureSection({ workspaceSlug, data, schema, onDataChange, showSaveMessage }: Props) {
  const [editItem, setEditItem] = useState<Partial<IShareholderEntry> | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [saving, setSaving] = useState(false);

  const startAdd = () => { setEditItem(empty()); setIsNew(true); };
  const startEdit = (item: IShareholderEntry) => { setEditItem({ ...item }); setIsNew(false); };
  const cancelEdit = () => { setEditItem(null); setIsNew(false); };

  const saveItem = async () => {
    if (!editItem) return;
    setSaving(true);
    try {
      if (isNew) {
        const created = await trinityService.createShareholder(workspaceSlug, editItem);
        onDataChange([...data, created]);
        showSaveMessage("Shareholder added");
      } else {
        const updated = await trinityService.updateShareholder(workspaceSlug, editItem.id!, editItem);
        onDataChange(data.map((d) => (d.id === updated.id ? updated : d)));
        showSaveMessage("Shareholder updated");
      }
      cancelEdit();
    } catch (err) { console.error(err); } finally { setSaving(false); }
  };

  const deleteItem = async (id: string) => {
    await trinityService.deleteShareholder(workspaceSlug, id);
    onDataChange(data.filter((d) => d.id !== id));
    showSaveMessage("Shareholder removed");
  };

  const totalShares = data.reduce((s, d) => s + (d.number_of_shares || 0), 0);
  const promoterPct = data.filter((d) => d.category !== "public")
    .reduce((s, d) => s + parseFloat(d.percentage_holding || "0"), 0);

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-custom-text-100">Capital Structure & Promoter Shareholding</h2>
        <p className="mt-1 text-sm text-custom-text-300">Shareholding pattern — promoters, promoter group, and public shareholders.</p>
        {schema && <ICDRClauseTag clause={schema.regulation_reference} />}
      </div>

      {data.length > 0 && (
        <div className="mb-4 grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-custom-border-200 bg-custom-background-90 p-3 text-center">
            <p className="text-lg font-semibold text-custom-text-100">{data.length}</p>
            <p className="text-xs text-custom-text-400">Shareholders</p>
          </div>
          <div className="rounded-lg border border-custom-border-200 bg-custom-background-90 p-3 text-center">
            <p className="text-lg font-semibold text-custom-text-100">{totalShares.toLocaleString()}</p>
            <p className="text-xs text-custom-text-400">Total Shares</p>
          </div>
          <div className="rounded-lg border border-custom-border-200 bg-custom-background-90 p-3 text-center">
            <p className="text-lg font-semibold text-custom-text-100">{promoterPct.toFixed(2)}%</p>
            <p className="text-xs text-custom-text-400">Promoter Holding</p>
          </div>
        </div>
      )}

      {data.map((item) => (
        <div key={item.id} className="mb-2 flex items-center justify-between rounded-lg border border-custom-border-200 bg-custom-background-90 px-4 py-3">
          <div>
            <span className="text-sm font-medium text-custom-text-100">{item.shareholder_name}</span>
            <span className="ml-2 rounded-full bg-custom-primary-100/10 px-2 py-0.5 text-[10px] font-medium text-custom-primary-100">
              {CATEGORY_OPTIONS.find((o) => o.value === item.category)?.label}
            </span>
            <p className="mt-0.5 text-xs text-custom-text-300">
              {item.number_of_shares.toLocaleString()} shares • {item.percentage_holding}% • {item.date_of_acquisition} @ ₹{item.acquisition_price_per_share}
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
          <h3 className="mb-4 text-sm font-semibold text-custom-text-200">{isNew ? "Add" : "Edit"} Shareholder</h3>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Name *</label>
              <input type="text" value={editItem.shareholder_name||""} onChange={(e)=>setEditItem(p=>({...p!,shareholder_name:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Category *</label>
              <select value={editItem.category||"promoter"} onChange={(e)=>setEditItem(p=>({...p!,category:e.target.value as any}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none">
                {CATEGORY_OPTIONS.map(o=>(<option key={o.value} value={o.value}>{o.label}</option>))}</select></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Shares *</label>
              <input type="number" min="0" value={editItem.number_of_shares||""} onChange={(e)=>setEditItem(p=>({...p!,number_of_shares:parseInt(e.target.value)||0}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Holding (%) *</label>
              <input type="number" step="0.01" value={editItem.percentage_holding||""} onChange={(e)=>setEditItem(p=>({...p!,percentage_holding:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Date of Acquisition *</label>
              <input type="date" value={editItem.date_of_acquisition||""} onChange={(e)=>setEditItem(p=>({...p!,date_of_acquisition:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
            <div><label className="mb-1 block text-xs font-medium text-custom-text-300">Price/Share (₹) *</label>
              <input type="number" step="0.01" value={editItem.acquisition_price_per_share||""} onChange={(e)=>setEditItem(p=>({...p!,acquisition_price_per_share:e.target.value}))} className="w-full rounded-md border border-custom-border-200 bg-custom-background-100 px-2.5 py-1.5 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none"/></div>
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={saveItem} disabled={saving} className="rounded-lg bg-custom-primary-100 px-4 py-2 text-sm font-medium text-white hover:bg-custom-primary-200 disabled:opacity-50">{saving?"Saving…":isNew?"Add":"Update"}</button>
            <button onClick={cancelEdit} className="rounded-lg border border-custom-border-200 px-4 py-2 text-sm font-medium text-custom-text-200 hover:bg-custom-background-80">Cancel</button>
          </div>
        </div>
      ) : (
        <button onClick={startAdd} className="mt-2 w-full rounded-lg border-2 border-dashed border-custom-border-200 px-4 py-6 text-sm text-custom-text-300 hover:border-custom-primary-100 hover:text-custom-primary-100">+ Add Shareholder</button>
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
