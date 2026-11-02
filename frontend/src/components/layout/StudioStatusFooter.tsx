import React from 'react';
import { Film } from 'lucide-react';

export const StudioStatusFooter: React.FC = () => {
  return (
    <footer
      className="mt-auto border-t py-3 px-6 text-xs transition-colors duration-200"
      style={{
        backgroundColor: 'var(--bg-footer)',
        borderColor: 'var(--border)',
        color: 'var(--text-muted)',
      }}
    >
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Film className="w-3.5 h-3.5 text-[#D6AD65]" />
          <span className="font-cinematic font-bold text-[#D6AD65]">FaceSwap</span>
          <span className="opacity-40">·</span>
          <span>AI-powered video face swap</span>
        </div>
        <span className="text-[11px] opacity-70">© {new Date().getFullYear()} FaceSwap. All rights reserved.</span>
      </div>
    </footer>
  );
};
