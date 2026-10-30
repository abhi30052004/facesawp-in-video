import React from 'react';
import { Film, UserCheck, ShieldCheck, Download, Sparkles } from 'lucide-react';
import { Card } from '../common/Card';

export const HowItWorksGuide: React.FC = () => {
  const steps = [
    {
      step: '01',
      title: 'Upload Cinematic Footage',
      desc: 'Import video clips up to 100MB and 60 seconds. Supports standard MP4, MOV, and WebM containers with instant playback preview.',
      icon: Film,
      accent: 'border-[#D6AD65]/30 text-[#D6AD65]',
    },
    {
      step: '02',
      title: 'Target Identity Selection',
      desc: 'Choose from iconic curated Bollywood archetype presets or upload a custom front-facing portrait with instant landmarks inspection.',
      icon: UserCheck,
      accent: 'border-[#8E3048]/40 text-[#FFA8BD]',
    },
    {
      step: '03',
      title: 'Consent & Neural Synthesis',
      desc: 'Verify likeness ethics before triggering BollyMesh v2.4 3D facial triangulation, subsurface scattering, and lighting harmony.',
      icon: ShieldCheck,
      accent: 'border-emerald-700/40 text-emerald-400',
    },
    {
      step: '04',
      title: 'Synchronized Master Review',
      desc: 'Inspect original vs neural output via side-by-side or split slider scrubbing. Export full 1080p preview with digital provenance.',
      icon: Download,
      accent: 'border-[#D6AD65]/30 text-[#D6AD65]',
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-cinematic font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#D6AD65]" />
            How BollySwap Studio Operates
          </h2>
          <p className="text-xs sm:text-sm text-[#8E8E9E]">
            End-to-end studio pipeline from raw video ingestion to master comparison export
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {steps.map((item) => {
          const Icon = item.icon;
          return (
            <Card
              key={item.step}
              hoverEffect
              className="p-5 flex flex-col justify-between relative overflow-hidden group"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-mono font-bold text-[#71717A] tracking-wider">
                  STAGE {item.step}
                </span>
                <div
                  className={`w-10 h-10 rounded-xl bg-[#1A1A24] border flex items-center justify-center transition-transform group-hover:scale-110 ${item.accent}`}
                >
                  <Icon className="w-5 h-5" />
                </div>
              </div>

              <div>
                <h3 className="text-base font-cinematic font-bold text-white mb-1.5 group-hover:text-[#D6AD65] transition-colors">
                  {item.title}
                </h3>
                <p className="text-xs text-[#8E8E9E] leading-relaxed">
                  {item.desc}
                </p>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};

