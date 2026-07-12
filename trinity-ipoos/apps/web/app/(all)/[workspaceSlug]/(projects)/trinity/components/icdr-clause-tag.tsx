/**
 * Trinity — ICDR Clause Tag Component
 * Displays the regulation reference for a field, with tooltip for full text.
 */

import { useState } from "react";

interface Props {
  clause: string;
  text?: string;
}

export function ICDRClauseTag({ clause, text }: Props) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        className="mt-1 inline-flex items-center gap-1 rounded-md bg-custom-primary-100/10 px-2 py-0.5 text-[10px] font-medium text-custom-primary-100 transition hover:bg-custom-primary-100/20"
        onMouseEnter={() => text && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => text && setShowTooltip((p) => !p)}
      >
        <span>📋</span>
        <span>{clause}</span>
      </button>
      {showTooltip && text && (
        <div className="absolute bottom-full left-0 z-50 mb-2 w-80 rounded-lg border border-custom-border-200 bg-custom-background-100 p-3 text-xs text-custom-text-200 shadow-lg">
          <p className="mb-1 font-semibold text-custom-text-100">{clause}</p>
          <p className="leading-relaxed">{text}</p>
        </div>
      )}
    </span>
  );
}
