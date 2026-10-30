import React, { useState } from 'react';
import { Info, Sparkles, X } from 'lucide-react';

export const DemoBanner: React.FC = () => {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="bg-gradient-to-r from-[#17171C] via-[#1D1A24] to-[#17171C] border-b border-[#D6AD65]/20 px-4 py-2 text-xs relative z-30">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5 text-[#E4D5B7]">
          <div className="p-1 rounded-md bg-[#D6AD65]/20 text-[#D6AD65]">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="font-semibold text-[#F4DE9C] mr-1">Phase 1 Interactive Preview:</span>
            <span className="text-[#A1A1AA]">
              BollySwap AI frontend studio experience. AI neural pipelines and downloads are simulated for interface validation. All actor presets and demo samples are synthetic demo placeholders.
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono text-[#D6AD65] bg-[#D6AD65]/10 px-2 py-0.5 rounded border border-[#D6AD65]/20">
            <Info className="w-3 h-3" />
            FastAPI Backend Ready
          </span>
          <button
            onClick={() => setDismissed(true)}
            aria-label="Dismiss banner"
            className="text-[#71717A] hover:text-[#EDEDED] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

