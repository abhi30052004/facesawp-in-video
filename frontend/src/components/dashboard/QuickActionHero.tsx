import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Clapperboard, Sparkles, Film, ArrowRight, ShieldCheck, Play } from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';

export const QuickActionHero: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-[#171720] via-[#15131A] to-[#0D0D11] border border-[#2B2B3C] p-6 sm:p-10 cinema-card-glow">
      {/* Decorative ambient background glows */}
      <div className="absolute -top-24 -right-24 w-96 h-96 bg-[#D6AD65]/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-[#8E3048]/15 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
        {/* Left Column Text */}
        <div className="max-w-2xl space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="gold" icon={<Sparkles className="w-3 h-3 text-[#D6AD65]" />}>
              BollySwap Virtual Studio v1.0
            </Badge>
            <span className="text-xs font-mono text-[#A1A1AA] flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              C2PA Synthetic Media Provenance
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-cinematic font-bold text-white tracking-wide leading-tight">
            Cinematic AI <span className="gold-gradient-text">Face Re-Targeting</span> for Indian Cinema
          </h1>

          <p className="text-sm sm:text-base text-[#A1A1AA] leading-relaxed">
            Re-imagine scenes with iconic Bollywood archetypes or custom talent. Studio-grade 3D mesh tracking, cinematic color harmony, and micro-expression temporal consistency.
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
              View Film Roster
            </Button>
          </div>
        </div>

        {/* Right Column Visual Teaser Card */}
        <div className="w-full lg:w-80 shrink-0">
          <div className="bg-[#121217]/90 border border-[#2D2D3E] rounded-2xl p-4 shadow-xl relative overflow-hidden group">
            <div className="aspect-[16/10] rounded-xl overflow-hidden relative mb-3 bg-black">
              <img
                src="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80"
                alt="Demo Preview Persona"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-end p-3">
                <span className="text-xs font-cinematic font-bold text-white flex items-center gap-1.5">
                  <Play className="w-3.5 h-3.5 fill-[#D6AD65] text-[#D6AD65]" />
                  Active Model: BollyMesh-v2.4
                </span>
              </div>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between items-center text-[#A1A1AA]">
                <span>Pipeline Mode</span>
                <span className="text-[#D6AD65] font-semibold">1080p Master Blend</span>
              </div>
              <div className="flex justify-between items-center text-[#A1A1AA]">
                <span>Face Anchors</span>
                <span className="font-mono text-white">468 Landmarks</span>
              </div>
              <div className="flex justify-between items-center text-[#A1A1AA]">
                <span>Audio Pass</span>
                <span className="text-emerald-400 font-mono">Synchronized</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

