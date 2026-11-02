import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Clapperboard, Film, ArrowRight } from 'lucide-react';
import { Button } from '../common/Button';

export const QuickActionHero: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div
      className="relative rounded-3xl overflow-hidden border p-6 sm:p-10 cinema-card-glow transition-colors duration-200"
      style={{
        backgroundColor: 'var(--bg-card)',
        borderColor: 'var(--border-card)',
        color: 'var(--text-primary)',
      }}
    >
      {/* Decorative ambient background glows */}
      <div className="absolute -top-24 -right-24 w-96 h-96 bg-[#D6AD65]/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-[#8E3048]/15 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
        {/* Left Column Text */}
        <div className="max-w-2xl space-y-4">
          <h1
            className="text-3xl sm:text-4xl lg:text-5xl font-cinematic font-bold tracking-wide leading-tight"
            style={{ color: 'var(--text-primary)' }}
          >
            AI <span className="gold-gradient-text">Face Swap</span> for Videos
          </h1>

          <p className="text-sm sm:text-base leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Upload any video, pick a target face, and let the AI do the rest. Fast, accurate, and natural-looking results every time.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-4">
            <Button
              size="lg"
              variant="primary"
              leftIcon={<Clapperboard className="w-5 h-5" />}
              rightIcon={<ArrowRight className="w-4 h-4 ml-1" />}
              onClick={() => navigate('/create')}
              className="cinema-gold-glow"
            >
              Start New Face Swap
            </Button>

            <Button
              size="lg"
              variant="secondary"
              leftIcon={<Film className="w-5 h-5 text-[#D6AD65]" />}
              onClick={() => navigate('/projects')}
            >
              My Projects
            </Button>
          </div>
        </div>

        {/* Right Column — simple info card */}
        <div className="w-full lg:w-72 shrink-0">
          <div
            className="rounded-2xl p-5 shadow-sm space-y-3 border transition-colors duration-200"
            style={{
              backgroundColor: 'var(--bg-input)',
              borderColor: 'var(--border)',
            }}
          >
            <p className="text-xs font-semibold text-[#D6AD65] uppercase tracking-widest">How it works</p>
            <div className="space-y-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-[#D6AD65]/15 border border-[#D6AD65]/30 text-[#D6AD65] text-xs flex items-center justify-center shrink-0 mt-0.5 font-bold">1</span>
                <span>Upload your source video</span>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-[#D6AD65]/15 border border-[#D6AD65]/30 text-[#D6AD65] text-xs flex items-center justify-center shrink-0 mt-0.5 font-bold">2</span>
                <span>Choose or upload a target face image</span>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-[#D6AD65]/15 border border-[#D6AD65]/30 text-[#D6AD65] text-xs flex items-center justify-center shrink-0 mt-0.5 font-bold">3</span>
                <span>Download your processed video</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
