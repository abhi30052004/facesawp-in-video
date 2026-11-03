import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { TargetFaceSelection, VideoMetadata } from '../../types/project';
import { Button } from '../common/Button';
import { bollySwapApi } from '../../services/api';

interface ProcessingStageViewProps {
  sourceVideo?: VideoMetadata;
  targetFace?: TargetFaceSelection;
  activeJob?: any;
  onProcessingComplete: (outputVideoUrl?: string) => void;
}

const STEPS = [
  { id: 1, label: 'Detecting Faces & Landmarks',    range: [0, 18]   },
  { id: 2, label: 'Building 3D Facial Mesh',        range: [18, 42]  },
  { id: 3, label: 'Neural Face Swap (CPU)',         range: [42, 84]  },
  { id: 4, label: 'Finalizing & Remuxing Audio',    range: [84, 100] },
];

const TIPS = [
  'AI is mapping 68 facial landmarks onto every frame.',
  'Ghost-256 model blends skin tone and lighting naturally.',
  'Original audio and background score are fully preserved.',
  'No footage ever leaves your machine — fully local CPU.',
  'Temporal smoothing removes any flicker between frames.',
];

export const ProcessingStageView: React.FC<ProcessingStageViewProps> = ({
  // sourceVideo unused in this minimal loader view
  targetFace,
  activeJob,
  onProcessingComplete,
}) => {
  const [progress, setProgress] = useState(
    activeJob?.progress ? Math.round(activeJob.progress * 100) : 5
  );
  const [elapsedSec, setElapsedSec] = useState(0);
  const [tipIdx, setTipIdx] = useState(0);

  // Elapsed ticker
  useEffect(() => {
    const t = setInterval(() => setElapsedSec(s => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Tip rotator every 5 s
  useEffect(() => {
    const t = setInterval(() => setTipIdx(i => (i + 1) % TIPS.length), 5000);
    return () => clearInterval(t);
  }, []);

  // Real backend polling
  useEffect(() => {
    if (!activeJob?.jobId) return;
    let mounted = true;
    let inFlight = false;
    const terminal = ['completed', 'failed', 'cancelled', 'model_not_configured'];

    const poll = async () => {
      if (!mounted || inFlight) return;
      inFlight = true;
      try {
        const job = await bollySwapApi.getSwapJob(activeJob.jobId);
        if (!job || !mounted) return;
        if (typeof job.progress === 'number') {
          setProgress(Math.max(5, Math.round(job.progress * 100)));
        }
        if (terminal.includes(job.status)) clearInterval(interval);
        if (job.status === 'completed') {
          setProgress(100);
          setTimeout(() => { if (mounted) onProcessingComplete(job.outputVideoUrl); }, 900);
        }
      } catch (_) { /* ignore */ }
      finally { inFlight = false; }
    };

    poll();
    const interval = setInterval(poll, 2500);
    return () => { mounted = false; clearInterval(interval); };
  }, [activeJob, onProcessingComplete]);

  // Demo progress simulation
  useEffect(() => {
    if (activeJob?.jobId) return;
    const t = setInterval(() => {
      setProgress(p => {
        if (p >= 99) {
          clearInterval(t);
          setTimeout(() => onProcessingComplete(), 800);
          return 100;
        }
        return p + (p < 30 ? 2 : p < 80 ? 1 : 2);
      });
    }, 1100);
    return () => clearInterval(t);
  }, [activeJob, onProcessingComplete]);

  const currentStep = useMemo(
    () => STEPS.find(s => progress >= s.range[0] && progress < s.range[1]) || STEPS[3],
    [progress]
  );

  const estRemaining = useMemo(() => {
    if (progress >= 100) return 'Done';
    if (elapsedSec < 3 || progress <= 5) return '~3 min';
    const total = elapsedSec / (progress / 100);
    const rem = Math.max(5, Math.round(total - elapsedSec));
    return rem > 60
      ? `~${Math.floor(rem / 60)}m ${String(rem % 60).padStart(2, '0')}s`
      : `~${rem}s`;
  }, [progress, elapsedSec]);

  const handleSkip = () => {
    setProgress(100);
    setTimeout(() => onProcessingComplete(), 600);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[520px] px-4 py-12 space-y-10">

      {/* ─── Orbital Loader ─── */}
      <div className="relative flex items-center justify-center select-none">

        {/* Outer orbit ring + travelling dot */}
        <motion.div
          className="absolute w-48 h-48 rounded-full"
          style={{ border: '1px dashed rgba(214,173,101,0.25)' }}
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 11, ease: 'linear' }}
        >
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full"
            style={{ background: '#D6AD65', boxShadow: '0 0 10px #D6AD65' }}
          />
        </motion.div>

        {/* Inner orbit ring + counter-dot */}
        <motion.div
          className="absolute w-32 h-32 rounded-full"
          style={{ border: '1px dashed rgba(142,48,72,0.3)' }}
          animate={{ rotate: -360 }}
          transition={{ repeat: Infinity, duration: 7.5, ease: 'linear' }}
        >
          <div
            className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-2 h-2 rounded-full"
            style={{ background: '#8E3048', boxShadow: '0 0 8px #8E3048' }}
          />
        </motion.div>

        {/* Ambient glow behind centre */}
        <motion.div
          className="absolute w-24 h-24 rounded-full blur-2xl"
          style={{ background: 'rgba(214,173,101,0.12)' }}
          animate={{ scale: [1, 1.5, 1], opacity: [0.4, 0.9, 0.4] }}
          transition={{ repeat: Infinity, duration: 2.8, ease: 'easeInOut' }}
        />

        {/* SVG circular progress arc */}
        <svg className="absolute w-48 h-48 -rotate-90" viewBox="0 0 160 160">
          <circle cx="80" cy="80" r="68" fill="none"
            stroke="rgba(255,255,255,0.04)" strokeWidth="3" />
          <defs>
            <linearGradient id="arcG" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#D6AD65" />
              <stop offset="100%" stopColor="#8E3048" />
            </linearGradient>
          </defs>
          <motion.circle
            cx="80" cy="80" r="68"
            fill="none"
            stroke="url(#arcG)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 68}`}
            animate={{ strokeDashoffset: 2 * Math.PI * 68 * (1 - progress / 100) }}
            transition={{ duration: 0.55, ease: 'easeOut' }}
          />
        </svg>

        {/* Centre avatar / icon */}
        <div
          className="relative z-10 w-20 h-20 rounded-full overflow-hidden flex items-center justify-center"
          style={{
            border: '2px solid rgba(214,173,101,0.35)',
            background: 'var(--bg-input)',
            boxShadow: '0 0 24px rgba(214,173,101,0.15)',
          }}
        >
          {targetFace?.previewUrl ? (
            <img src={targetFace.previewUrl} alt="" className="w-full h-full object-cover" />
          ) : (
            <Sparkles className="w-7 h-7" style={{ color: '#D6AD65' }} />
          )}
          {/* Laser scan line */}
          <motion.div
            className="absolute left-0 right-0 h-0.5"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(214,173,101,0.8), transparent)' }}
            animate={{ top: ['0%', '100%', '0%'] }}
            transition={{ repeat: Infinity, duration: 2.2, ease: 'easeInOut' }}
          />
        </div>

        {/* Floating % badge */}
        <div
          className="absolute -bottom-9 text-2xl font-bold font-mono"
          style={{ color: 'var(--text-primary)' }}
        >
          {progress}%
        </div>
      </div>

      {/* ─── Title ─── */}
      <div className="text-center space-y-1.5 pt-4">
        <h3 className="text-2xl font-cinematic font-bold" style={{ color: 'var(--text-primary)' }}>
          {progress >= 100 ? 'Face Swap Complete ✓' : 'Synthesizing Face Swap'}
        </h3>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          {progress >= 100 ? 'Your video is ready. Preparing download…' : currentStep.label}
        </p>
      </div>

      {/* ─── Slim progress bar ─── */}
      <div className="w-full max-w-sm space-y-2">
        <div
          className="w-full h-1.5 rounded-full overflow-hidden"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
        >
          <motion.div
            className="h-full rounded-full relative overflow-hidden"
            style={{ background: 'linear-gradient(90deg, #D6AD65, #F4DE9C, #8E3048)' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          >
            {/* shimmer sweep */}
            <motion.div
              className="absolute inset-0"
              style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)' }}
              animate={{ x: ['-100%', '200%'] }}
              transition={{ repeat: Infinity, duration: 1.8, ease: 'linear' }}
            />
          </motion.div>
        </div>

        <div className="flex justify-between text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          <span>{elapsedSec}s elapsed</span>
          <span>{estRemaining} remaining</span>
        </div>
      </div>

      {/* ─── Step pills ─── */}
      <div className="flex flex-wrap justify-center gap-2 max-w-md">
        {STEPS.map(step => {
          const done   = progress >= step.range[1];
          const active = !done && progress >= step.range[0];
          return (
            <div
              key={step.id}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-500"
              style={{
                background: done
                  ? 'rgba(52,211,153,0.08)'
                  : active
                  ? 'rgba(214,173,101,0.12)'
                  : 'transparent',
                borderColor: done
                  ? 'rgba(52,211,153,0.3)'
                  : active
                  ? 'var(--gold)'
                  : 'var(--border)',
                color: done
                  ? '#6ee7b7'
                  : active
                  ? '#D6AD65'
                  : 'var(--text-muted)',
                opacity: !done && !active ? 0.45 : 1,
              }}
            >
              {done   ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> :
               active ? <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" /> :
                        <div className="w-3 h-3 rounded-full border border-current shrink-0" />}
              {step.label}
            </div>
          );
        })}
      </div>

      {/* ─── Rotating tip ─── */}
      <AnimatePresence mode="wait">
        <motion.p
          key={tipIdx}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.35 }}
          className="max-w-xs text-center text-xs px-5 py-2.5 rounded-xl"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            color: 'var(--text-secondary)',
          }}
        >
          💡 {TIPS[tipIdx]}
        </motion.p>
      </AnimatePresence>

      {/* ─── Skip (demo only) ─── */}
      {!activeJob?.jobId && (
        <Button size="sm" variant="ghost" onClick={handleSkip}
          className="text-xs opacity-40 hover:opacity-80">
          Skip preview
        </Button>
      )}
    </div>
  );
};
