import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  Loader2,
  Terminal,
  FastForward,
  Sparkles,
  Clock,
  Activity,
} from 'lucide-react';
import { DEMO_PIPELINE_STAGES } from '../../services/mockData';
import { TargetFaceSelection, VideoMetadata } from '../../types/project';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';

interface ProcessingStageViewProps {
  sourceVideo?: VideoMetadata;
  targetFace?: TargetFaceSelection;
  onProcessingComplete: () => void;
}

export const ProcessingStageView: React.FC<ProcessingStageViewProps> = ({
  sourceVideo,
  targetFace,
  onProcessingComplete,
}) => {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [progress, setProgress] = useState(5);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [logs, setLogs] = useState<string[]>([
    'Initializing BollyMesh AI runtime environment...',
    'Demuxing video container: ' + (sourceVideo?.name || 'input_stream.mp4'),
  ]);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll log box
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Timer ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSec((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Realistic stage progression
  useEffect(() => {
    const stage = DEMO_PIPELINE_STAGES[currentStageIdx];
    if (!stage) return;

    const stageLogs: Record<number, string[]> = {
      0: [
        'Decoding H.264 stream into 30fps working frames...',
        'Generated 450 frame buffers in memory cache.',
        'Assessing motion vectors and camera shake index: 0.04 (Stable)',
      ],
      1: [
        `Registering target face identity: ${targetFace?.name || 'Selected Persona'}`,
        'Computed 468 landmark anchor vectors on source actor.',
        'Estimating 3D head pitch (4.2°), roll (-1.1°), and yaw (6.8°)...',
        'Generating dense face mesh triangulation with pupil tracking.',
      ],
      2: [
        'Encoding latent identity embeddings via BollyMesh Transformer...',
        'Synthesizing photorealistic skin texture and subsurface scattering...',
        'Volumetric lighting harmony: matching key light and ambient fill...',
        'Blending facial perimeter with hairline occlusion boundaries.',
      ],
      3: [
        'Executing temporal anti-flickering pass across 450 frames...',
        'Preserving micro-expressions and blink synchronization...',
        'Remuxing 48kHz stereo AAC audio pass-through...',
        'Encoding 1080p master preview container. Finalizing export checksum.',
      ],
    };

    const newStageLogs = stageLogs[currentStageIdx] || [];
    const timeouts: ReturnType<typeof setTimeout>[] = [];

    newStageLogs.forEach((msg, idx) => {
      const t = setTimeout(() => {
        setLogs((prev) => [...prev, `[STAGE ${currentStageIdx + 1}] ${msg}`]);
      }, (idx + 1) * 700);
      timeouts.push(t);
    });

    const progressStep = 100 / DEMO_PIPELINE_STAGES.length;
    const targetProgress = Math.min(100, Math.round((currentStageIdx + 1) * progressStep));

    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev < targetProgress) {
          return prev + 2;
        }
        return prev;
      });
    }, 150);

    const advanceTimer = setTimeout(() => {
      if (currentStageIdx < DEMO_PIPELINE_STAGES.length - 1) {
        setCurrentStageIdx((prev) => prev + 1);
      } else {
        setProgress(100);
        setTimeout(() => {
          onProcessingComplete();
        }, 1200);
      }
    }, stage.durationMs);

    return () => {
      clearInterval(progressInterval);
      clearTimeout(advanceTimer);
      timeouts.forEach((t) => clearTimeout(t));
    };
  }, [currentStageIdx, targetFace, sourceVideo, onProcessingComplete]);

  // Fast-forward simulation helper for immediate evaluation
  const handleFastForward = () => {
    setProgress(100);
    setLogs((prev) => [
      ...prev,
      '[SIMULATION NOTE] User fast-forwarded demo rendering simulation.',
      '[COMPLETED] Master comparison renders ready for inspection.',
    ]);
    setTimeout(() => {
      onProcessingComplete();
    }, 600);
  };

  const totalDuration = DEMO_PIPELINE_STAGES.reduce((acc, s) => acc + s.durationMs, 0) / 1000;
  const remainingSec = Math.max(0, Math.round(totalDuration - elapsedSec));

  return (
    <div className="space-y-6">
      {/* Honest Simulation Disclaimer Alert */}
      <div className="p-4 rounded-xl bg-[#1A1813] border border-[#D6AD65]/30 flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-[#D6AD65]/20 text-[#D6AD65] shrink-0 mt-0.5">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-[#F4DE9C]">
                Demo Pipeline Simulation Active
              </span>
              <Badge variant="demo">Phase 1 Frontend State</Badge>
            </div>
            <p className="text-xs text-[#A1A1AA] mt-1 leading-relaxed">
              This interactive processing screen simulates the real multi-stage neural pipeline with telemetry, stage progressions, and frame logs. When the FastAPI backend is hooked up in Phase 2, this view binds directly to live worker task streams.
            </p>
          </div>
        </div>

        <Button
          size="sm"
          variant="outline"
          leftIcon={<FastForward className="w-3.5 h-3.5" />}
          onClick={handleFastForward}
          className="shrink-0 text-xs hidden sm:inline-flex"
        >
          Fast-Forward Demo
        </Button>
      </div>

      {/* Progress & Time Hero Card */}
      <div className="bg-[#15151C] border border-[#272736] rounded-2xl p-6 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <span className="text-xs font-mono text-[#D6AD65] uppercase tracking-wider flex items-center gap-1.5 mb-1">
              <Activity className="w-3.5 h-3.5 animate-pulse text-[#D6AD65]" />
              Stage {currentStageIdx + 1} of {DEMO_PIPELINE_STAGES.length}: {DEMO_PIPELINE_STAGES[currentStageIdx]?.title}
            </span>
            <h3 className="text-xl sm:text-2xl font-cinematic font-bold text-white">
              Synthesizing Identity Re-enactment
            </h3>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-[#A1A1AA] bg-[#1C1C26] px-3 py-1.5 rounded-lg border border-[#2B2B38]">
              <Clock className="w-3.5 h-3.5 text-[#D6AD65]" />
              <span>Elapsed: {elapsedSec}s</span>
            </div>
            <div className="flex items-center gap-1.5 text-[#A1A1AA] bg-[#1C1C26] px-3 py-1.5 rounded-lg border border-[#2B2B38]">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#8E3048]" />
              <span>Est. Remaining: ~{remainingSec}s</span>
            </div>
          </div>
        </div>

        {/* Big Progress bar */}
        <div className="space-y-2">
          <div className="w-full bg-[#20202C] h-3 rounded-full overflow-hidden p-0.5">
            <motion.div
              className="bg-gradient-to-r from-[#D6AD65] via-[#E0BC75] to-[#8E3048] h-full rounded-full"
              initial={{ width: '5%' }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="flex justify-between items-center text-xs font-mono text-[#8E8E9E]">
            <span>Telemetry: Frame-Level Alignment</span>
            <span className="text-white font-bold">{progress}% Complete</span>
          </div>
        </div>
      </div>

      {/* 4 Pipeline Stages Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {DEMO_PIPELINE_STAGES.map((stage, idx) => {
          const isDone = idx < currentStageIdx;
          const isActive = idx === currentStageIdx;
          const isPending = idx > currentStageIdx;

          return (
            <div
              key={stage.id}
              className={`p-4 rounded-xl border transition-all duration-300 relative ${
                isActive
                  ? 'bg-gradient-to-b from-[#1C1A16] to-[#15151C] border-[#D6AD65] shadow-[0_0_15px_rgba(214,173,101,0.15)]'
                  : isDone
                  ? 'bg-[#15151B] border-[#2A382A]'
                  : 'bg-[#121217] border-[#20202B] opacity-60'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-mono text-[#71717A]">STEP 0{idx + 1}</span>
                {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                {isActive && <Loader2 className="w-4 h-4 text-[#D6AD65] animate-spin" />}
                {isPending && <div className="w-2 h-2 rounded-full bg-[#2A2A38]" />}
              </div>

              <h4 className="text-xs font-semibold text-white mb-1 leading-snug">
                {stage.title}
              </h4>
              <p className="text-[11px] text-[#8E8E9E] line-clamp-2 leading-relaxed">
                {stage.detail}
              </p>
            </div>
          );
        })}
      </div>

      {/* Live Stream Terminal Logs */}
      <div className="bg-[#0C0C10] border border-[#22222E] rounded-xl overflow-hidden shadow-inner">
        <div className="px-4 py-2 bg-[#121218] border-b border-[#20202B] flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-mono text-[#A1A1AA]">
            <Terminal className="w-3.5 h-3.5 text-[#D6AD65]" />
            <span>Neural Engine Console Stream</span>
          </div>
          <span className="text-[10px] font-mono text-[#71717A]">
            BollyMesh-v2.4 [PyTorch 2.3 | CUDA 12.2]
          </span>
        </div>

        <div
          ref={logContainerRef}
          className="p-4 h-44 overflow-y-auto font-mono text-xs space-y-1.5 text-left"
        >
          {logs.map((log, i) => (
            <div key={i} className="flex items-start gap-2 text-[#9A9AA8]">
              <span className="text-[#D6AD65] select-none">{'>'}</span>
              <span className={log.includes('STAGE') ? 'text-[#F4DE9C]' : 'text-[#B0B0C0]'}>
                {log}
              </span>
            </div>
          ))}
          <div className="text-[#D6AD65] animate-pulse">_</div>
        </div>
      </div>
    </div>
  );
};
