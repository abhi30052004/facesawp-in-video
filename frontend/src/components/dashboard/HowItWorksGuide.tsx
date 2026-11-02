import React from 'react';
import { Film, UserCheck, ShieldCheck, Download, Sparkles } from 'lucide-react';
import { Card } from '../common/Card';

export const HowItWorksGuide: React.FC = () => {
  const steps = [
    {
      step: '01',
      title: 'Upload Your Video',
      desc: 'Upload a video clip (MP4, MOV, or WebM). Supports files up to 100MB and 60 seconds long.',
      icon: Film,
      accent: 'border-[#D6AD65]/30 text-[#D6AD65]',
    },
    {
      step: '02',
      title: 'Select a Target Face',
      desc: 'Upload a clear, front-facing photo of the person whose face you want to use in the video.',
      icon: UserCheck,
      accent: 'border-[#8E3048]/40 text-[#B84764]',
    },
    {
      step: '03',
      title: 'Process & Swap',
      desc: 'Our AI model detects and replaces the face in each frame, preserving natural expressions and lighting.',
      icon: ShieldCheck,
      accent: 'border-emerald-600/40 text-emerald-500',
    },
    {
      step: '04',
      title: 'Review & Download',
      desc: 'Preview the result side-by-side with the original, then download your finished video.',
      icon: Download,
      accent: 'border-[#D6AD65]/30 text-[#D6AD65]',
    },
  ];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2
            className="text-xl font-cinematic font-bold flex items-center gap-2"
            style={{ color: 'var(--text-primary)' }}
          >
            <Sparkles className="w-5 h-5 text-[#D6AD65]" />
            How It Works
          </h2>
          <p className="text-xs sm:text-sm" style={{ color: 'var(--text-faint)' }}>
            Four simple steps from video upload to download
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
                <span className="text-xs font-mono font-bold tracking-wider" style={{ color: 'var(--text-muted)' }}>
                  STEP {item.step}
                </span>
                <div
                  className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-transform group-hover:scale-110 ${item.accent}`}
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                  }}
                >
                  <Icon className="w-5 h-5" />
                </div>
              </div>

              <div>
                <h3
                  className="text-base font-cinematic font-bold mb-1.5 group-hover:text-[#D6AD65] transition-colors"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {item.title}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-faint)' }}>
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
