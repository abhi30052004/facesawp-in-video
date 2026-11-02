import React, { useState, useRef } from 'react';
import {
  Play,
  Pause,
  Download,
  RotateCcw,
  Sparkles,
  Film,
  Sliders,
  Columns,
  Info,
  Check,
} from 'lucide-react';
import { TargetFaceSelection, VideoMetadata } from '../../types/project';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { formatDuration } from '../../utils/formatters';

interface ResultsComparisonViewProps {
  sourceVideo?: VideoMetadata;
  targetFace?: TargetFaceSelection;
  outputVideoUrl?: string;
  onReset: () => void;
  onSaveToProjects: () => void;
}

export const ResultsComparisonView: React.FC<ResultsComparisonViewProps> = ({
  sourceVideo,
  targetFace,
  outputVideoUrl,
  onReset,
  onSaveToProjects,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(15);
  const [comparisonMode, setComparisonMode] = useState<'side-by-side' | 'split'>('side-by-side');
  const [splitPosition, setSplitPosition] = useState(50);
  const [isSaved, setIsSaved] = useState(false);
  const [showDownloadNote, setShowDownloadNote] = useState(false);

  const originalVideoRef = useRef<HTMLVideoElement>(null);
  const swappedVideoRef = useRef<HTMLVideoElement>(null);

  const videoUrl =
    sourceVideo?.url ||
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4';
  const swappedVideoUrl = outputVideoUrl || videoUrl;

  const togglePlay = () => {
    if (isPlaying) {
      originalVideoRef.current?.pause();
      swappedVideoRef.current?.pause();
      setIsPlaying(false);
    } else {
      originalVideoRef.current?.play();
      swappedVideoRef.current?.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (originalVideoRef.current) {
      setCurrentTime(originalVideoRef.current.currentTime);
      if (originalVideoRef.current.duration) {
        setDuration(originalVideoRef.current.duration);
      }
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (originalVideoRef.current) originalVideoRef.current.currentTime = time;
    if (swappedVideoRef.current) swappedVideoRef.current.currentTime = time;
  };

  const handleOriginalPlay = () => {
    if (swappedVideoRef.current && originalVideoRef.current) {
      swappedVideoRef.current.currentTime = originalVideoRef.current.currentTime;
      swappedVideoRef.current.play().catch(() => {});
    }
    setIsPlaying(true);
  };

  const handleOriginalPause = () => {
    if (swappedVideoRef.current) {
      swappedVideoRef.current.pause();
    }
    setIsPlaying(false);
  };

  const handleDownload = () => {
    setShowDownloadNote(true);
    const link = document.createElement('a');
    link.href = swappedVideoUrl;
    link.download = `FaceSwap_Result_${Date.now()}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleSave = () => {
    onSaveToProjects();
    setIsSaved(true);
  };

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2
              className="text-xl font-cinematic font-bold flex items-center gap-2"
              style={{ color: 'var(--text-primary)' }}
            >
              <Sparkles className="w-5 h-5 text-[#D6AD65]" />
              Video Comparison & Export
            </h2>
            <Badge variant="demo">Preview</Badge>
          </div>
          <p className="text-xs sm:text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            Synchronized comparison playback. Target persona:{' '}
            <span className="font-semibold" style={{ color: 'var(--gold)' }}>{targetFace?.name || 'Selected Persona'}</span>
          </p>
        </div>

        {/* View Mode Toggle & Save/Download CTA */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Comparison Mode Pill */}
          <div
            className="flex p-1 rounded-xl text-xs border"
            style={{
              backgroundColor: 'var(--bg-input)',
              borderColor: 'var(--border)',
            }}
          >
            <button
              onClick={() => setComparisonMode('side-by-side')}
              className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer font-medium"
              style={{
                backgroundColor: comparisonMode === 'side-by-side' ? 'var(--gold)' : 'transparent',
                color: comparisonMode === 'side-by-side' ? '#09090B' : 'var(--text-secondary)',
                fontWeight: comparisonMode === 'side-by-side' ? 600 : 500,
              }}
            >
              <Columns className="w-3.5 h-3.5" />
              Side-by-Side
            </button>
            <button
              onClick={() => setComparisonMode('split')}
              className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer font-medium"
              style={{
                backgroundColor: comparisonMode === 'split' ? 'var(--gold)' : 'transparent',
                color: comparisonMode === 'split' ? '#09090B' : 'var(--text-secondary)',
                fontWeight: comparisonMode === 'split' ? 600 : 500,
              }}
            >
              <Sliders className="w-3.5 h-3.5" />
              Split Slider
            </button>
          </div>

          <Button
            size="sm"
            variant={isSaved ? 'secondary' : 'burgundy'}
            leftIcon={isSaved ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Film className="w-3.5 h-3.5" />}
            onClick={handleSave}
            disabled={isSaved}
          >
            {isSaved ? 'Saved to Projects' : 'Save to Projects'}
          </Button>

          <Button
            size="sm"
            variant="primary"
            leftIcon={<Download className="w-3.5 h-3.5" />}
            onClick={handleDownload}
          >
            Download Video
          </Button>
        </div>
      </div>

      {/* Download info note */}
      {showDownloadNote && (
        <div
          className="p-3.5 rounded-xl border flex items-start gap-2.5 text-xs"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
            color: 'var(--text-secondary)',
          }}
        >
          <Info className="w-4 h-4 text-[#D6AD65] shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold" style={{ color: 'var(--text-primary)' }}>Export Initiated</p>
            <p className="mt-0.5" style={{ color: 'var(--text-faint)' }}>
              The video stream has been dispatched for download to your device.
            </p>
          </div>
        </div>
      )}

      {/* Video Comparison Arena */}
      <div
        className="rounded-2xl overflow-hidden shadow-lg border"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border)',
        }}
      >
        {/* Arena Screen */}
        <div className="relative aspect-video max-h-[500px] bg-black flex items-center justify-center overflow-hidden">
          {comparisonMode === 'side-by-side' ? (
            /* SIDE BY SIDE MODE */
            <div className="w-full h-full grid grid-cols-2 divide-x divide-white/10">
              {/* Left: Original Footage */}
              <div className="relative h-full bg-black flex items-center justify-center overflow-hidden">
                <video
                  ref={originalVideoRef}
                  src={videoUrl}
                  className="w-full h-full object-contain"
                  onTimeUpdate={handleTimeUpdate}
                  onPlay={handleOriginalPlay}
                  onPause={handleOriginalPause}
                  playsInline
                />
                <div className="absolute top-3 left-3">
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-black/70 text-[#A1A1AA] border border-white/10">
                    Original Video
                  </span>
                </div>
              </div>

              {/* Right: Swapped Video */}
              <div className="relative h-full bg-black flex items-center justify-center overflow-hidden">
                <video
                  ref={swappedVideoRef}
                  src={swappedVideoUrl}
                  className="w-full h-full object-contain"
                  playsInline
                />
                <div className="absolute top-3 right-3 flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-[#D6AD65]/20 text-[#F4DE9C] border border-[#D6AD65]/40 font-semibold">
                    Face Swapped
                  </span>
                </div>
              </div>
            </div>
          ) : (
            /* SPLIT SLIDER MODE */
            <div
              className="relative w-full h-full bg-black flex items-center justify-center overflow-hidden select-none"
              onMouseMove={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const pos = ((e.clientX - rect.left) / rect.width) * 100;
                setSplitPosition(Math.max(0, Math.min(100, pos)));
              }}
            >
              {/* Bottom Layer: Swapped Video */}
              <div className="absolute inset-0">
                <video
                  ref={swappedVideoRef}
                  src={swappedVideoUrl}
                  className="w-full h-full object-contain"
                  playsInline
                />
              </div>

              {/* Top Layer: Original Footage clipped by splitPosition */}
              <div
                className="absolute inset-0 overflow-hidden"
                style={{ width: `${splitPosition}%` }}
              >
                <video
                  ref={originalVideoRef}
                  src={videoUrl}
                  className="w-full h-full object-contain max-w-none"
                  style={{ width: '100%', height: '100%' }}
                  onTimeUpdate={handleTimeUpdate}
                  onPlay={handleOriginalPlay}
                  onPause={handleOriginalPause}
                  playsInline
                />
              </div>

              {/* Splitter Divider Bar */}
              <div
                className="absolute top-0 bottom-0 w-1 bg-[#D6AD65] shadow-[0_0_15px_#D6AD65] pointer-events-none"
                style={{ left: `${splitPosition}%` }}
              >
                <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-[#D6AD65] text-[#09090B] flex items-center justify-center font-bold text-xs shadow-xl">
                  <Sliders className="w-4 h-4 rotate-90" />
                </div>
              </div>

              {/* Split Overlay Labels */}
              <div className="absolute top-3 left-3 pointer-events-none">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/70 text-[#A1A1AA] border border-white/10">
                  Original (Left)
                </span>
              </div>
              <div className="absolute top-3 right-3 pointer-events-none">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#D6AD65]/20 text-[#F4DE9C] border border-[#D6AD65]/40">
                  Face Swapped (Right)
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Unified Master Playback Control Bar */}
        <div
          className="p-4 border-t space-y-3"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
          }}
        >
          {/* Scrub timeline */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-[#D6AD65] min-w-[40px]">
              {formatDuration(currentTime)}
            </span>
            <input
              type="range"
              min={0}
              max={duration || 15}
              step={0.1}
              value={currentTime}
              onChange={handleSeek}
              className="flex-1 h-1.5 rounded-lg appearance-none cursor-pointer accent-[#D6AD65]"
              style={{ backgroundColor: 'var(--border)' }}
            />
            <span className="text-xs font-mono min-w-[40px]" style={{ color: 'var(--text-muted)' }}>
              {formatDuration(duration)}
            </span>
          </div>

          {/* Controls Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={togglePlay}
                aria-label={isPlaying ? 'Pause master player' : 'Play master player'}
                className="w-10 h-10 rounded-xl bg-gradient-to-r from-[#D6AD65] to-[#B89246] text-[#09090B] flex items-center justify-center font-bold hover:brightness-110 transition-all cursor-pointer shadow-md"
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </button>

              <span className="text-xs hidden sm:inline" style={{ color: 'var(--text-faint)' }}>
                Synchronized dual-stream preview
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                onClick={onReset}
              >
                New Swap
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
