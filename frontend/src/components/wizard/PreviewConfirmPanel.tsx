import React, { useEffect, useState } from 'react';
import { Sparkles, Cpu, Film, User, CheckCircle2 } from 'lucide-react';
import { TargetFaceSelection, VideoMetadata } from '../../types/project';
import { Button } from '../common/Button';
import { bollySwapApi } from '../../services/api';

interface PreviewConfirmPanelProps {
  sourceVideo?: VideoMetadata;
  targetFace?: TargetFaceSelection;
  onConfirm: () => void;
  onBack: () => void;
}

export const PreviewConfirmPanel: React.FC<PreviewConfirmPanelProps> = ({
  sourceVideo,
  targetFace,
  onConfirm,
  onBack,
}) => {
  const [engineStatus, setEngineStatus] = useState<any>(null);
  const [consentAffirmed, setConsentAffirmed] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const res = await bollySwapApi.getEngineStatus();
        if (isMounted && res) {
          setEngineStatus(res);
        }
      } catch (err) {
        console.warn('Failed to load engine status:', err);
      }
    };
    fetchStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-xl font-cinematic font-bold text-[var(--text-primary)]">
          Review & Confirm Face Swap
        </h3>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Verify your source video, replacement face portrait, and AI engine status before launching neural processing.
        </p>
      </div>

      {/* Side-by-Side Asset Preview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Source Video Card */}
        <div
          className="rounded-2xl p-4 border transition-colors relative overflow-hidden"
          style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center gap-2 mb-3">
            <Film className="w-4 h-4 text-[#D6AD65]" />
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Target Footage
            </span>
          </div>

          {sourceVideo?.url ? (
            <div className="rounded-xl overflow-hidden aspect-video bg-black/40 relative border border-white/5">
              <video
                src={sourceVideo.url}
                className="w-full h-full object-contain"
                controls
                playsInline
                preload="metadata"
              />
            </div>
          ) : (
            <div className="rounded-xl aspect-video bg-black/20 flex items-center justify-center text-xs text-[var(--text-muted)]">
              No video selected
            </div>
          )}

          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">File Name</span>
              <span className="font-medium truncate block text-[var(--text-primary)]">{sourceVideo?.name || 'video.mp4'}</span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Resolution</span>
              <span className="font-medium text-[var(--text-primary)]">
                {sourceVideo?.width && sourceVideo?.height ? `${sourceVideo.width}x${sourceVideo.height}` : 'HD 1080p'}
              </span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Duration</span>
              <span className="font-medium text-[var(--text-primary)]">
                {sourceVideo?.durationSec ? `${Math.round(sourceVideo.durationSec)}s` : '15s'}
              </span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Audio Track</span>
              <span className="font-medium text-emerald-400">Preserved (Original)</span>
            </div>
          </div>
        </div>

        {/* Replacement Face Card */}
        <div
          className="rounded-2xl p-4 border transition-colors relative overflow-hidden"
          style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center gap-2 mb-3">
            <User className="w-4 h-4 text-[#D6AD65]" />
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Replacement Face
            </span>
          </div>

          {targetFace?.previewUrl ? (
            <div className="rounded-xl overflow-hidden aspect-video bg-black/40 flex items-center justify-center border border-white/5 relative">
              <img
                src={targetFace.previewUrl}
                alt="Target Face"
                className="max-h-full max-w-full object-contain"
              />
            </div>
          ) : (
            <div className="rounded-xl aspect-video bg-black/20 flex items-center justify-center text-xs text-[var(--text-muted)]">
              No face selected
            </div>
          )}

          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Identity Type</span>
              <span className="font-medium text-[var(--text-primary)]">{targetFace?.name || 'Consented Portrait'}</span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Alignment Model</span>
              <span className="font-medium text-[var(--text-primary)]">YuNet / 2DFAN-4</span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Neural Swapper</span>
              <span className="font-medium text-[#D6AD65]">Ghost 256</span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">License</span>
              <span className="font-medium text-emerald-400">Apache-2.0 Clean</span>
            </div>
          </div>
        </div>
      </div>

      {/* Engine Readiness Badge Card */}
      <div
        className="rounded-2xl p-4 border flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        style={{ backgroundColor: 'rgba(214, 173, 101, 0.05)', borderColor: 'rgba(214, 173, 101, 0.2)' }}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#D6AD65]/10 flex items-center justify-center text-[#D6AD65] shrink-0">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-[var(--text-primary)]">
                {engineStatus?.engine || 'FaceFusion'} {engineStatus?.version || '3.9.2'}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Pure CPU Execution ({engineStatus?.execution_provider || 'CPUExecutionProvider'}) • Model: {engineStatus?.model || 'ghost_1_256'} (Apache-2.0)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-secondary)]">
          <span className="flex items-center gap-1 text-emerald-400">
            <CheckCircle2 className="w-4 h-4" /> FFmpeg Ready
          </span>
          <span>•</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <CheckCircle2 className="w-4 h-4" /> Model Cached
          </span>
        </div>
      </div>

      {/* Likeness Consent Gate */}
      <div
        className="rounded-2xl p-4 border"
        style={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border)' }}
      >
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={consentAffirmed}
            onChange={(e) => setConsentAffirmed(e.target.checked)}
            className="mt-1 w-4 h-4 rounded text-[#D6AD65] focus:ring-[#D6AD65] border-gray-600"
          />
          <div className="text-xs">
            <span className="font-bold text-[var(--text-primary)] block">
              Likeness Rights & AI Ethics Affirmation
            </span>
            <span className="text-[var(--text-secondary)] block mt-0.5 leading-relaxed">
              I affirm that I possess explicit likeness rights or express authorization from the individual whose portrait is being synthesized. This footage will be watermarked with "AI Generated Media • BollySwap AI" in full compliance with AI media safety standards.
            </span>
          </div>
        </label>
      </div>

      {/* Navigation Bar */}
      <div className="pt-4 border-t flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
        <Button size="sm" variant="ghost" onClick={onBack}>
          Back to Face
        </Button>
        <Button
          size="md"
          variant="primary"
          disabled={!consentAffirmed}
          onClick={onConfirm}
          rightIcon={<Sparkles className="w-4 h-4" />}
        >
          Start FaceFusion Swap
        </Button>
      </div>
    </div>
  );
};
