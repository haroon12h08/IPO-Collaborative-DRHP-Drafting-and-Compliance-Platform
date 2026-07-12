/**
 * Trinity — Setup Section Component
 * Initializes the IPO workspace with company details.
 */

import { useState, useEffect } from "react";
import type { IIPOWorkspace } from "@/services/trinity.service";

interface Props {
  workspaceSlug: string;
  ipoWorkspace: IIPOWorkspace | null;
  onSave: (data: Partial<IIPOWorkspace>) => Promise<void>;
  saving: boolean;
}

export function SetupSection({ workspaceSlug, ipoWorkspace, onSave, saving }: Props) {
  const [formData, setFormData] = useState({
    company_name: "",
    cin: "",
    exchange_target: "nse_emerge" as "nse_emerge" | "bse_sme",
  });

  useEffect(() => {
    if (ipoWorkspace) {
      setFormData({
        company_name: ipoWorkspace.company_name || "",
        cin: ipoWorkspace.cin || "",
        exchange_target: ipoWorkspace.exchange_target || "nse_emerge",
      });
    }
  }, [ipoWorkspace]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-custom-text-100">Company Setup</h2>
        <p className="mt-1 text-sm text-custom-text-300">
          Initialize your Trinity Intelligence IPO workspace. This information will be used across all DRHP
          disclosure sections.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Company Name */}
        <div>
          <label htmlFor="company_name" className="mb-1.5 block text-sm font-medium text-custom-text-200">
            Company Legal Name <span className="text-red-500">*</span>
          </label>
          <input
            id="company_name"
            type="text"
            required
            value={formData.company_name}
            onChange={(e) => setFormData((p) => ({ ...p, company_name: e.target.value }))}
            placeholder="e.g., ABC Manufacturing Ltd."
            className="w-full rounded-lg border border-custom-border-200 bg-custom-background-100 px-3 py-2 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none focus:ring-1 focus:ring-custom-primary-100"
          />
        </div>

        {/* CIN */}
        <div>
          <label htmlFor="cin" className="mb-1.5 block text-sm font-medium text-custom-text-200">
            Corporate Identity Number (CIN)
          </label>
          <input
            id="cin"
            type="text"
            value={formData.cin}
            onChange={(e) => setFormData((p) => ({ ...p, cin: e.target.value }))}
            placeholder="e.g., U72200KA2015PTC082024"
            maxLength={21}
            className="w-full rounded-lg border border-custom-border-200 bg-custom-background-100 px-3 py-2 text-sm text-custom-text-100 placeholder:text-custom-text-400 focus:border-custom-primary-100 focus:outline-none focus:ring-1 focus:ring-custom-primary-100"
          />
          <p className="mt-1 text-xs text-custom-text-400">21-character alphanumeric code from MCA</p>
        </div>

        {/* Exchange Target */}
        <div>
          <label htmlFor="exchange_target" className="mb-1.5 block text-sm font-medium text-custom-text-200">
            Target Exchange <span className="text-red-500">*</span>
          </label>
          <select
            id="exchange_target"
            value={formData.exchange_target}
            onChange={(e) =>
              setFormData((p) => ({ ...p, exchange_target: e.target.value as "nse_emerge" | "bse_sme" }))
            }
            className="w-full rounded-lg border border-custom-border-200 bg-custom-background-100 px-3 py-2 text-sm text-custom-text-100 focus:border-custom-primary-100 focus:outline-none focus:ring-1 focus:ring-custom-primary-100"
          >
            <option value="nse_emerge">NSE Emerge (SME Platform)</option>
            <option value="bse_sme">BSE SME Platform</option>
          </select>
        </div>

        {/* Info Box */}
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/30">
          <h4 className="text-sm font-medium text-blue-800 dark:text-blue-300">
            📋 What happens next?
          </h4>
          <p className="mt-1 text-xs text-blue-700 dark:text-blue-400">
            After setup, you'll be guided through 5 disclosure sections required by SEBI ICDR
            Regulations 2018, Chapter IX. Each field shows the specific regulation clause it maps to.
            You can save progress at any time and return later.
          </p>
        </div>

        <button
          type="submit"
          disabled={saving || !formData.company_name}
          className="rounded-lg bg-custom-primary-100 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-custom-primary-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving…" : ipoWorkspace ? "Update Company Details" : "Initialize Trinity Intelligence IPO Workspace"}
        </button>
      </form>
    </div>
  );
}
