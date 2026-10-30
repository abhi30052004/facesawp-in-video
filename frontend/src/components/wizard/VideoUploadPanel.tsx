import React, { useState, useRef } from 'react';
import { Upload, Film, AlertCircle, Play, Pause, RotateCcw, Sparkles, Loader2 } from 'lucide-react';
import { VideoMetadata } from '../../types/project';
import { extractVideoMetadata, validateVideoFile } from '../../utils/mediaValidation';
import { formatBytes, formatDuration } from '../../utils/formatters';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { DEMO_SAMPLE_VIDEOS } from '../../services/mockData';
import { bollySwapApi } from '../../services/api';

interface VideoUploadPanelProps {
  currentVideo?: VideoMetadata;
  onVideoSelected: (video: VideoMetadata) => void;
  onClearVideo: () => void;
}

export const VideoUploadPanel: React.FC<VideoUploadPanelProps> = ({
  currentVideo,
  onVideoSelected,
  onClearVideo,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setIsAnalyzing(true);
    setUploadProgress(0);

    try {
      const basicValidation = validateVideoFile(file);
      if (!basicValidation.isValid) {
        setError(basicValidation.error || 'Invalid video file');
        setIsAnalyzing(false);
        setUploadProgress(null);
        return;
      }

      // Extract client-side metadata
      const metaResult = await extractVideoMetadata(file);
      if (!metaResult.isValid || !metaResult.data) {
        setError(metaResult.error || 'Failed to decode video stream');
        setIsAnalyzing(false);
        setUploadProgress(null);
        return;
      }

      // Stream to real backend upload endpoint if enabled
      const uploadRes = await bollySwapApi.uploadVideo(file, (percent) => {
        setUploadProgress(percent);
      });

      const finalMetadata: VideoMetadata = {
        ...metaResult.data,
        uploadId: uploadRes.fileId,
        url: uploadRes.storageUrl || metaResult.data.url,
      };

      onVideoSelected(finalMetadata);
    } catch (err: any) {
      setError(err?.message || 'An unexpected error occurred while uploading the video.');
    } finally {
      setIsAnalyzing(false);
      setUploadProgress(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const togglePlayback = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  return (
    <div className="space-y-6">
      {/* Instructions header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-xl font-cinematic font-bold text-white flex items-center gap-2">
            <Film className="w-5 h-5 text-[#D6AD65]" />
            Step 1: Source Cinematic Footage
          </h2>
          <p className="text-xs sm:text-sm text-[#A1A1AA]">
            Upload the scene where the actor's face will be reenacted.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="gold">Max 100MB</Badge>
          <Badge variant="slate">Max 60 Seconds</Badge>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 flex items-start gap-3 text-red-200 text-sm">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-red-300">File Validation Failed</p>
            <p className="text-xs text-red-200/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Main Container: Upload Drag & Drop OR Video Preview Player */}
      {!currentVideo ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all cursor-pointer relative overflow-hidden group ${
            isDragging
              ? 'border-[#D6AD65] bg-[#D6AD65]/10 scale-[0.99]'
              : 'border-[#2C2C3A] hover:border-[#D6AD65]/50 bg-[#141419]/80 hover:bg-[#181822]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.mov,.webm,video/mp4,video/quicktime,video/webm"
            className="hidden"
            onChange={handleInputChange}
          />

          <div className="flex flex-col items-center max-w-md mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-[#20202B] border border-[#2F2F3F] flex items-center justify-center text-[#D6AD65] mb-4 group-hover:scale-110 group-hover:border-[#D6AD65]/50 transition-all shadow-lg">
              <Upload className="w-7 h-7" />
            </div>

            <h3 className="text-base font-semibold text-white mb-1">
              Drag & drop your video clip here
            </h3>
            <p className="text-xs text-[#8E8E9E] mb-4">
              Supports MP4, MOV, or WebM format. Crisp lighting & clear facial visibility recommended.
            </p>

            {uploadProgress !== null ? (
              <div className="w-full space-y-2 mt-2">
                <div className="flex justify-between items-center text-xs font-mono text-[#D6AD65]">
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Streaming to Studio Storage...
                  </span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-[#20202B] h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-[#D6AD65] to-[#8E3048] h-full transition-all duration-300 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                isLoading={isAnalyzing}
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                Browse Local Files
              </Button>
            )}
          </div>
        </div>
      ) : (
        /* Video Preview Card */
        <div className="bg-[#14141A] border border-[#2A2A38] rounded-2xl overflow-hidden shadow-2xl">
          <div className="relative aspect-video max-h-[420px] bg-black flex items-center justify-center group">
            <video
              ref={videoRef}
              src={currentVideo.url}
              className="w-full h-full object-contain"
              onEnded={() => setIsPlaying(false)}
            />

            {/* Play/Pause Overlay Button */}
            <button
              onClick={togglePlayback}
              aria-label={isPlaying ? 'Pause video' : 'Play video'}
              className="absolute inset-0 m-auto w-14 h-14 rounded-full bg-black/60 backdrop-blur-md border border-[#D6AD65]/40 text-[#D6AD65] flex items-center justify-center hover:scale-110 transition-all cursor-pointer shadow-xl"
            >
              {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-0.5" />}
            </button>

            {/* Video status tag */}
            <div className="absolute top-3 left-3 flex items-center gap-2">
              <Badge variant="gold">
                {currentVideo.isDemoSample ? 'Demo Clip' : 'Uploaded Footage'}
              </Badge>
              <span className="text-[11px] font-mono bg-black/70 px-2 py-0.5 rounded text-white border border-white/10">
                {currentVideo.width}x{currentVideo.height} • {currentVideo.fps || 30} FPS
              </span>
            </div>
          </div>

          {/* Footage Specs Bar */}
          <div className="p-4 bg-[#171720] border-t border-[#262635] flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[#20202C] text-[#D6AD65]">
                <Film className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white truncate max-w-[280px] sm:max-w-md">
                  {currentVideo.name}
                </p>
                <p className="text-xs text-[#8E8E9E] font-mono">
                  {formatBytes(currentVideo.sizeBytes)} • Duration: {formatDuration(currentVideo.durationSec)} • {currentVideo.format.toUpperCase()}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                onClick={onClearVideo}
              >
                Change Video
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Quick Demo Clip Presets Selector */}
      <div className="pt-2 border-t border-[#22222E]">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-[#D6AD65] uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            Quick Demo Clips (Instant Exploration)
          </span>
          <span className="text-[11px] text-[#71717A]">
            Select pre-packaged footage to test the pipeline immediately
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {DEMO_SAMPLE_VIDEOS.map((demo) => (
            <div
              key={demo.name}
              onClick={() => onVideoSelected(demo)}
              className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                currentVideo?.name === demo.name
                  ? 'border-[#D6AD65] bg-[#D6AD65]/10 shadow-[0_0_15px_rgba(214,173,101,0.15)]'
                  : 'border-[#252532] hover:border-[#38384A] bg-[#15151B]'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#20202A] flex items-center justify-center text-[#D6AD65]">
                  <Film className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-medium text-white">{demo.name.replace('.mp4', '')}</p>
                  <p className="text-[11px] text-[#8E8E9E] font-mono">
                    {demo.width}x{demo.height} • {demo.durationSec}s • Demo
                  </p>
                </div>
              </div>

              <span className="text-xs text-[#D6AD65] font-semibold">Select</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

