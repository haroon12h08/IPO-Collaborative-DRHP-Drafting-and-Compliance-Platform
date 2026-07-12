/**
 * Trinity IPO Preparation — Multi-Step Wizard Page
 *
 * Walks the user through 5 DRHP disclosure sections, one at a time.
 * Saves progress incrementally via the Trinity API.
 * Loads ICDR clause metadata from the backend schemas endpoint.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router";
import { TrinityService } from "@/services/trinity.service";
import type {
  IIPOWorkspace,
  IObjectsOfIssue,
  IRelatedPartyTransaction,
  IShareholderEntry,
  ILitigationEntry,
  IFinancialYearSummary,
  IICDRSchema,
  IUseOfProceeds,
} from "@/services/trinity.service";

// Section components
import { SetupSection } from "./components/setup-section";
import { ObjectsOfIssueSection } from "./components/objects-of-issue";
import { RelatedPartySection } from "./components/related-party";
import { CapitalStructureSection } from "./components/capital-structure";
import { LitigationSection } from "./components/litigation";
import { FinancialSummarySection } from "./components/financial-summary";

const trinityService = new TrinityService();

const SECTIONS = [
  { key: "setup", label: "Company Setup", icon: "🏢", description: "Initialize your Trinity Intelligence IPO workspace" },
  { key: "objects_of_issue", label: "Objects of the Issue", icon: "🎯", description: "ICDR Schedule VI, Clause 2(1)" },
  { key: "related_party_transactions", label: "Related Party Transactions", icon: "🤝", description: "ICDR Schedule VI, Clause 14" },
  { key: "capital_structure", label: "Capital Structure", icon: "📊", description: "ICDR Schedule VI, Clauses 4 & 5" },
  { key: "litigation", label: "Litigation & Regulatory", icon: "⚖️", description: "ICDR Schedule VI, Clause 17" },
  { key: "financial_summary", label: "Financial Summary", icon: "💰", description: "ICDR Schedule VI, Clause 10" },
] as const;

export default function TrinityWizardPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const [activeSection, setActiveSection] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  // Data state
  const [ipoWorkspace, setIpoWorkspace] = useState<IIPOWorkspace | null>(null);
  const [objectsOfIssue, setObjectsOfIssue] = useState<IObjectsOfIssue | null>(null);
  const [rpts, setRpts] = useState<IRelatedPartyTransaction[]>([]);
  const [shareholders, setShareholders] = useState<IShareholderEntry[]>([]);
  const [litigations, setLitigations] = useState<ILitigationEntry[]>([]);
  const [financials, setFinancials] = useState<IFinancialYearSummary[]>([]);
  const [schemas, setSchemas] = useState<Record<string, IICDRSchema>>({});

  // Load all data on mount
  useEffect(() => {
    if (!workspaceSlug) return;

    const loadData = async () => {
      setLoading(true);
      try {
        // Load schemas
        const schemasData = await trinityService.fetchAllSchemas(workspaceSlug);
        setSchemas(schemasData);

        // Load IPO workspace
        const ws = await trinityService.fetchIPOWorkspace(workspaceSlug);
        if (ws.exists !== false) {
          setIpoWorkspace(ws);

          // Load all section data in parallel
          const [ooi, rptsData, shData, litData, finData] = await Promise.all([
            trinityService.fetchObjectsOfIssue(workspaceSlug).catch(() => null),
            trinityService.fetchRPTs(workspaceSlug).catch(() => []),
            trinityService.fetchShareholders(workspaceSlug).catch(() => []),
            trinityService.fetchLitigations(workspaceSlug).catch(() => []),
            trinityService.fetchFinancials(workspaceSlug).catch(() => []),
          ]);

          if (ooi && ooi.exists !== false) setObjectsOfIssue(ooi);
          setRpts(rptsData);
          setShareholders(shData);
          setLitigations(litData);
          setFinancials(finData);

          // Jump to first incomplete section
          setActiveSection(1);
        }
      } catch (err) {
        console.error("Failed to load Trinity data:", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [workspaceSlug]);

  // Show save feedback
  const showSaveMessage = useCallback((msg: string) => {
    setSaveMessage(msg);
    setTimeout(() => setSaveMessage(""), 3000);
  }, []);

  // Section completion check
  const sectionComplete = useMemo(() => ({
    setup: !!ipoWorkspace,
    objects_of_issue: !!objectsOfIssue?.fresh_issue_amount,
    related_party_transactions: rpts.length > 0,
    capital_structure: shareholders.length > 0,
    litigation: litigations.length > 0,
    financial_summary: financials.length > 0,
  }), [ipoWorkspace, objectsOfIssue, rpts, shareholders, litigations, financials]);

  const completedCount = Object.values(sectionComplete).filter(Boolean).length;
  const progressPercent = Math.round((completedCount / SECTIONS.length) * 100);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-custom-background-100">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-custom-primary-100 border-t-transparent" />
          <p className="text-sm text-custom-text-300">Loading Trinity Intelligence IPO Workspace…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-custom-background-100">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-custom-border-200 bg-custom-background-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-custom-text-100">
              Trinity Intelligence
            </h1>
            <p className="mt-1 text-sm text-custom-text-300">
              {ipoWorkspace
                ? `${ipoWorkspace.company_name} • DRHP Disclosure Data Collection`
                : "Set up your Trinity Intelligence IPO workspace to begin"}
            </p>
          </div>
          <div className="flex items-center gap-4">
            {saveMessage && (
              <span className="rounded-full bg-green-500/10 px-3 py-1 text-xs font-medium text-green-600">
                {saveMessage}
              </span>
            )}
            <div className="flex items-center gap-2">
              <div className="h-2 w-32 overflow-hidden rounded-full bg-custom-background-80">
                <div
                  className="h-full rounded-full bg-custom-primary-100 transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <span className="text-xs font-medium text-custom-text-300">
                {completedCount}/{SECTIONS.length}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Navigation */}
        <nav className="w-72 flex-shrink-0 overflow-y-auto border-r border-custom-border-200 bg-custom-background-90 px-3 py-4">
          <div className="mb-4 px-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-custom-text-400">
              Disclosure Sections
            </h3>
          </div>
          {SECTIONS.map((section, idx) => {
            const isActive = idx === activeSection;
            const isComplete = sectionComplete[section.key as keyof typeof sectionComplete];
            const isDisabled = idx > 0 && !ipoWorkspace;

            return (
              <button
                key={section.key}
                onClick={() => !isDisabled && setActiveSection(idx)}
                disabled={isDisabled}
                className={`mb-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-all ${
                  isActive
                    ? "bg-custom-primary-100/10 text-custom-primary-100"
                    : isDisabled
                      ? "cursor-not-allowed opacity-40"
                      : "text-custom-text-200 hover:bg-custom-background-80"
                }`}
              >
                <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-custom-background-80 text-base">
                  {isComplete ? "✓" : section.icon}
                </span>
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-sm font-medium ${isActive ? "text-custom-primary-100" : ""}`}>
                    {section.label}
                  </p>
                  <p className="truncate text-xs text-custom-text-400">
                    {section.description}
                  </p>
                </div>
                {isComplete && (
                  <span className="flex-shrink-0 rounded-full bg-green-500/10 px-1.5 py-0.5 text-[10px] font-medium text-green-600">
                    Done
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          <div className="mx-auto max-w-3xl">
            {activeSection === 0 && (
              <SetupSection
                workspaceSlug={workspaceSlug!}
                ipoWorkspace={ipoWorkspace}
                onSave={async (data) => {
                  setSaving(true);
                  try {
                    if (ipoWorkspace) {
                      const updated = await trinityService.updateIPOWorkspace(workspaceSlug!, data);
                      setIpoWorkspace(updated);
                    } else {
                      const created = await trinityService.createIPOWorkspace(workspaceSlug!, data);
                      setIpoWorkspace(created);
                    }
                    showSaveMessage("Company setup saved");
                  } finally {
                    setSaving(false);
                  }
                }}
                saving={saving}
              />
            )}

            {activeSection === 1 && (
              <ObjectsOfIssueSection
                workspaceSlug={workspaceSlug!}
                data={objectsOfIssue}
                schema={schemas.objects_of_issue}
                rpts={rpts}
                shareholders={shareholders}
                onSave={async (data) => {
                  setSaving(true);
                  try {
                    const saved = await trinityService.saveObjectsOfIssue(workspaceSlug!, data);
                    setObjectsOfIssue(saved);
                    showSaveMessage("Objects of the Issue saved");
                  } finally {
                    setSaving(false);
                  }
                }}
                saving={saving}
              />
            )}

            {activeSection === 2 && (
              <RelatedPartySection
                workspaceSlug={workspaceSlug!}
                data={rpts}
                schema={schemas.related_party_transactions}
                onDataChange={setRpts}
                showSaveMessage={showSaveMessage}
              />
            )}

            {activeSection === 3 && (
              <CapitalStructureSection
                workspaceSlug={workspaceSlug!}
                data={shareholders}
                schema={schemas.capital_structure}
                onDataChange={setShareholders}
                showSaveMessage={showSaveMessage}
              />
            )}

            {activeSection === 4 && (
              <LitigationSection
                workspaceSlug={workspaceSlug!}
                data={litigations}
                schema={schemas.litigation}
                onDataChange={setLitigations}
                showSaveMessage={showSaveMessage}
              />
            )}

            {activeSection === 5 && (
              <FinancialSummarySection
                workspaceSlug={workspaceSlug!}
                data={financials}
                schema={schemas.financial_summary}
                onDataChange={setFinancials}
                showSaveMessage={showSaveMessage}
              />
            )}

            {/* Navigation Buttons */}
            <div className="mt-8 flex items-center justify-between border-t border-custom-border-200 pt-6">
              <button
                onClick={() => setActiveSection((p) => Math.max(0, p - 1))}
                disabled={activeSection === 0}
                className="rounded-lg border border-custom-border-200 px-4 py-2 text-sm font-medium text-custom-text-200 transition hover:bg-custom-background-80 disabled:cursor-not-allowed disabled:opacity-40"
              >
                ← Previous
              </button>
              <button
                onClick={() => setActiveSection((p) => Math.min(SECTIONS.length - 1, p + 1))}
                disabled={activeSection === SECTIONS.length - 1 || (!ipoWorkspace && activeSection === 0)}
                className="rounded-lg bg-custom-primary-100 px-4 py-2 text-sm font-medium text-white transition hover:bg-custom-primary-200 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
