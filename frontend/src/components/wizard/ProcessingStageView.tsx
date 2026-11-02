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
  AlertTriangle,
  FileCode,
  ArrowRight,
} from 'lucide-react';
import { DEMO_PIPELINE_STAGES } from '../../services/mockData';
import { TargetFaceSelection, VideoMetadata } from '../../types/project';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { bollySwapApi } from '../../services/api';

interface ProcessingStageViewProps {
  sourceVideo?: VideoMetadata;
  targetFace?: TargetFaceSelection;
  activeJob?: any;
  onProcessingComplete: (outputVideoUrl?: string) => void;
}

export const ProcessingStageView: React.FC<ProcessingStageViewProps> = ({
  sourceVideo,
  targetFace,
  activeJob,
  onProcessingComplete,
}) => {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [progress, setProgress] = useState(activeJob?.progress ? Math.round(activeJob.progress * 100) : 10);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [isModelNotConfigured, setIsModelNotConfigured] = useState(
    activeJob?.status === 'model_not_configured'
  );
  const [jobStatus, setJobStatus] = useState<string>(activeJob?.status || 'processing');
  const [currentStepMessage, setCurrentStepMessage] = useState<string>(
    activeJob?.currentStep || 'Validated project assets, video readability, and likeness consent.'
  );

  const [logs, setLogs] = useState<string[]>([
    activeJob
      ? `Registered Job ID: ${activeJob.jobId} (Status: ${activeJob.status})`
      : 'Initializing AI processing environment...',
    'Demuxing video container: ' + (sourceVideo?.name || 'input_stream.mp4'),
    'Face Detection & Alignment initialized.',
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

  // Live Backend Polling if an active job is provided
  useEffect(() => {
    if (!activeJob?.jobId) return;

    let isMounted = true;
    let inFlight = false;
    const terminalStatuses = ['completed', 'failed', 'cancelled', 'model_not_configured'];

    const poll = async () => {
      if (!isMounted || inFlight) return;
      inFlight = true;
      try {
        const liveJob = await bollySwapApi.getSwapJob(activeJob.jobId);
        if (!liveJob || !isMounted) return;

        setJobStatus(liveJob.status);
        if (liveJob.currentStep) {
          setCurrentStepMessage(liveJob.currentStep);
        }

        if (typeof liveJob.progress === 'number') {
          setProgress(Math.round(liveJob.progress * 100));
        }

        if (terminalStatuses.includes(liveJob.status)) {
          clearInterval(pollInterval);
        }

        if (liveJob.status === 'model_not_configured') {
          setIsModelNotConfigured(true);
          setLogs((prev) => [
            ...prev,
            `[ENGINE STATUS] ${liveJob.currentStep}`,
            '[NOTICE] Neural inference unconfigured. Pipeline assets and tracking verified.',
          ]);
        } else if (liveJob.status === 'completed') {
          setProgress(100);
          setLogs((prev) => [
            ...prev,
            '[COMPLETED] Master face replacement rendered successfully.',
          ]);
          setTimeout(() => {
            if (isMounted) {
              onProcessingComplete(liveJob.outputVideoUrl);
            }
          }, 800);
          clearInterval(pollInterval);
        } else if (liveJob.status === 'failed') {
          setLogs((prev) => [
            ...prev,
            `[FAILED] ${liveJob.errorMessage || 'Processing job terminated.'}`,
          ]);
        }
      } catch (err) {
        console.warn('Job polling request error:', err);
      } finally {
        inFlight = false;
      }
    };

    poll();
    const pollInterval = setInterval(poll, 2000);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
    };
  }, [activeJob, onProcessingComplete]);

  // Fallback stage progression for demo mode
  useEffect(() => {
    if (activeJob?.jobId && isModelNotConfigured) return;
    if (activeJob?.jobId && jobStatus === 'completed') return;

    const stage = DEMO_PIPELINE_STAGES[currentStageIdx];
    if (!stage) return;

    const stageLogs: Record<number, string[]> = {
      0: [
        'Decoding video stream into working frames...',
        'Generated frame buffers in memory cache.',
        'Assessing motion vectors and camera stability...',
      ],
      1: [
        `Registering target face: ${targetFace?.name || 'Selected Persona'}`,
        'Computing facial landmarks and alignment...',
        'Generating transformation matrices...',
      ],
      2: [
        'Executing face swap model...',
        'Harmonizing ambient lighting & skin tone...',
        'Compositing face canvas without boundary seams...',
      ],
      3: [
        'Executing temporal tracking & smoothing pass...',
        'Preserving original audio track...',
        'Finalizing video file...',
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
      } else if (!activeJob?.jobId) {
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
  }, [currentStageIdx, targetFace, sourceVideo, activeJob, isModelNotConfigured, jobStatus, onProcessingComplete]);

  // Fast-forward simulation helper for immediate evaluation
  const handleFastForward = () => {
    setProgress(100);
    setLogs((prev) => [
      ...prev,
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
      {/* Simulation Active Notice */}
      <div
        className="p-4 rounded-xl border flex items-start justify-between gap-4 transition-colors"
        style={{
          backgroundColor: 'rgba(214, 173, 101, 0.1)',
          borderColor: 'var(--gold)',
        }}
      >
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-[#D6AD65]/20 text-[#D6AD65] shrink-0 mt-0.5">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                {activeJob?.jobId ? 'Video Processing Pipeline Active' : 'Processing Simulation Active'}
              </span>
              <Badge variant="demo">{activeJob?.jobId ? 'Backend Pipeline' : 'Preview Mode'}</Badge>
            </div>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {activeJob?.jobId
                ? 'Video processing stream executing: audio extraction, face detection, alignment, and container synthesis.'
                : 'Processing screen demonstrating the multi-stage pipeline with real-time stage progressions and logs.'}
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
          Fast-Forward
        </Button>
      </div>

      {/* Progress & Time Hero Card */}
      <div
        className="border rounded-2xl p-6 relative overflow-hidden transition-colors"
        style={{
          backgroundColor: 'var(--bg-input)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <span className="text-xs font-mono text-[#D6AD65] uppercase tracking-wider flex items-center gap-1.5 mb-1">
              <Activity className="w-3.5 h-3.5 animate-pulse text-[#D6AD65]" />
              Stage {currentStageIdx + 1} of {DEMO_PIPELINE_STAGES.length}: {DEMO_PIPELINE_STAGES[currentStageIdx]?.title}
            </span>
            <h3 className="text-xl sm:text-2xl font-cinematic font-bold" style={{ color: 'var(--text-primary)' }}>
              {isModelNotConfigured ? 'Pipeline Ready' : 'Synthesizing Face Swap'}
            </h3>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderColor: 'var(--border)',
                color: 'var(--text-secondary)',
              }}
            >
              <Clock className="w-3.5 h-3.5 text-[#D6AD65]" />
              <span>Elapsed: {elapsedSec}s</span>
            </div>
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderColor: 'var(--border)',
                color: 'var(--text-secondary)',
              }}
            >
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#8E3048]" />
              <span>{isModelNotConfigured ? 'Status: Ready' : `Est. Remaining: ~${remainingSec}s`}</span>
            </div>
          </div>
        </div>

        {/* Big Progress bar */}
        <div className="space-y-2">
          <div className="w-full h-3 rounded-full overflow-hidden p-0.5 border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
            <motion.div
              className="bg-gradient-to-r from-[#D6AD65] via-[#E0BC75] to-[#8E3048] h-full rounded-full"
              initial={{ width: '5%' }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="flex justify-between items-center text-xs font-mono" style={{ color: 'var(--text-faint)' }}>
            <span>Status: {currentStepMessage}</span>
            <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{progress}% Complete</span>
          </div>
        </div>
      </div>

      {/* 4 Pipeline Stages Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {DEMO_PIPELINE_STAGES.map((stage, idx) => {
          const isDone = isModelNotConfigured || idx < currentStageIdx;
          const isActive = !isModelNotConfigured && idx === currentStageIdx;

          return (
            <div
              key={stage.id}
              className="p-4 rounded-xl border transition-all duration-300 relative"
              style={{
                backgroundColor: isActive ? 'rgba(214, 173, 101, 0.12)' : 'var(--bg-input)',
                borderColor: isActive ? 'var(--gold)' : 'var(--border)',
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--text-muted)' }}>
                  STAGE 0{idx + 1}
                </span>
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                ) : isActive ? (
                  <Loader2 className="w-4 h-4 text-[#D6AD65] animate-spin" />
                ) : (
                  <div className="w-2 h-2 rounded-full border" style={{ borderColor: 'var(--border)' }} />
                )}
              </div>

              <h4 className="text-xs font-semibold mb-1 leading-snug" style={{ color: 'var(--text-primary)' }}>
                {stage.title}
              </h4>
              <p className="text-[11px] line-clamp-2 leading-relaxed" style={{ color: 'var(--text-faint)' }}>
                {stage.detail}
              </p>
            </div>
          );
        })}
      </div>

      {/* Live Stream Terminal Logs */}
      <div
        className="rounded-xl overflow-hidden border shadow-inner"
        style={{
          backgroundColor: 'var(--bg-input)',
          borderColor: 'var(--border)',
        }}
      >
        <div
          className="px-4 py-2 border-b flex items-center justify-between"
          style={{
            backgroundColor: 'var(--bg-card)',
            borderColor: 'var(--border)',
          }}
        >
          <div className="flex items-center gap-2 text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
            <Terminal className="w-3.5 h-3.5 text-[#D6AD65]" />
            <span>Process Console Stream</span>
          </div>
        </div>

        <div
          ref={logContainerRef}
          className="p-4 h-44 overflow-y-auto font-mono text-xs space-y-1.5 text-left"
          style={{ color: 'var(--text-secondary)' }}
        >
          {logs.map((log, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-[#D6AD65] select-none">{'>'}</span>
              <span
                className={
                  log.includes('STAGE')
                    ? 'text-[#B8822A] dark:text-[#F4DE9C]'
                    : log.includes('ERROR')
                    ? 'text-red-500'
                    : log.includes('NOTICE') || log.includes('COMPLETED')
                    ? 'text-emerald-500 dark:text-emerald-300'
                    : 'inherit'
                }
              >
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
