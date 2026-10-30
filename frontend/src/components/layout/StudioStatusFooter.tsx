import React from 'react';
import { Film, Cpu, HardDrive, HeartHandshake } from 'lucide-react';
import { useProjects } from '../../context/ProjectContext';

export const StudioStatusFooter: React.FC = () => {
  const { stats } = useProjects();

  return (
    <footer className="mt-auto border-t border-[#1C1C26] bg-[#0C0C10] py-4 px-6 text-xs text-[#7A7A8A]">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left Studio details */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-[#D6AD65]">
            <Film className="w-3.5 h-3.5" />
            <span className="font-cinematic font-bold">BollySwap AI</span>
          </div>
          <span className="text-[#3A3A4A]">|</span>
          <span>Phase 1 Architecture (Vite + React 19 + Tailwind v4)</span>
          <span className="text-[#3A3A4A]">|</span>
          <span className="text-emerald-400 font-mono">FastAPI API Layer Ready</span>
        </div>

        {/* Right metrics */}
        <div className="flex flex-wrap items-center gap-5 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 text-[#A1A1AA]">
            <Cpu className="w-3.5 h-3.5 text-[#D6AD65]" />
            <span>GPU Mesh: Ready</span>
          </div>
          <div className="flex items-center gap-1.5 text-[#A1A1AA]">
            <HardDrive className="w-3.5 h-3.5 text-[#8E3048]" />
            <span>
              {(stats.storageUsedMb / 1024).toFixed(1)} GB / {(stats.storageLimitMb / 1024).toFixed(0)} GB
            </span>
          </div>
          <div className="flex items-center gap-1 text-[#D6AD65]">
            <HeartHandshake className="w-3.5 h-3.5" />
            <span>Ethical AI Compliance 2.1</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

