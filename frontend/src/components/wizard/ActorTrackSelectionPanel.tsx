import React, { useState } from 'react';
import {
  Sparkles,
  UserCheck,
  Clock,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Loader2,
  Scan,
  ShieldCheck,
  Video,
} from 'lucide-react';
import { DetectedActorTrack, VideoMetadata } from '../../types/project';
import { bollySwapApi } from '../../services/api';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';

interface ActorTrackSelectionPanelProps {
  projectId: string;
  sourceVideo?: VideoMetadata;
  detectedTracks: DetectedActorTrack[];
  selectedTrackId?: string;
  onTracksDetected: (tracks: DetectedActorTrack[], defaultSelectedId?: string) => void;
  onTrackSelected: (trackId: string) => void;
}

export const ActorTrackSelectionPanel: React.FC<ActorTrackSelectionPanelProps> = ({
  projectId,
  sourceVideo,
  detectedTracks,
  selectedTrackId,
  onTracksDetected,
  onTrackSelected,
}) => {
  const [isDetecting, setIsDetecting] = useState(false);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [hasScanned, setHasScanned] = useState(detectedTracks.length > 0);

  const handleRunDetection = async () => {
    if (!sourceVideo?.uploadId) {
      setError('Please upload a source video footage first before running face detection.');
      return;
    }

    setIsDetecting(true);
    setError(null);
    setCurrentStage('Initializing OpenCV YuNet Face Detection Pipeline...');

    try {
      setCurrentStage('Extracting and sampling video frames at 1.5s intervals...');
      const result = await bollySwapApi.detectFaces(projectId, sourceVideo.uploadId);

      setHasScanned(true);
      setCurrentStage('Analysis complete.');

      const tracks = result.tracks || [];
      const defaultId = result.selectedTrackId || (tracks.length > 0 ? tracks[0].trackId : undefined);
      onTracksDetected(tracks, defaultId);
    } catch (err: any) {
      setError(
        err?.message ||
          'Face detection failed. Ensure the backend server is running and the video contains readable frames.'
      );
    } finally {
      setIsDetecting(false);
    }
  };

  const handleSelectTrack = async (trackId: string) => {
    onTrackSelected(trackId);
    try {
      await bollySwapApi.selectProjectActorTrack(projectId, trackId);
    } catch (err) {
      console.warn('Backend track selection persistence skipped or pending:', err);
    }
  };

  const resolveThumbnailUrl = (track: DetectedActorTrack): string => {
    if (track.thumbnailUrl && track.thumbnailUrl.startsWith('http')) {
      return track.thumbnailUrl;
    }
    if (track.thumbnailFileId) {
      return bollySwapApi.getFileUrl(track.thumbnailFileId);
    }
    return track.thumbnailUrl || '';
  };

  return (
    <div className="space-y-6 pt-4 border-t border-[#242434]">
      {/* Header with Title and Tech Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Scan className="w-5 h-5 text-[#D6AD65]" />
            <h3 className="text-base sm:text-lg font-cinematic font-bold text-white tracking-wide">
              Actor Face Detection in Footage
            </h3>
            <Badge variant="gold" size="sm">
              OpenCV YuNet (CPU)
            </Badge>
          </div>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Scans footage using lightweight neural inference to locate actors and group continuous appearances across timestamps.
          </p>
        </div>

        {/* Action Button */}
        {!isDetecting && (
          <Button
            size="sm"
            variant={detectedTracks.length > 0 ? 'secondary' : 'primary'}
            leftIcon={detectedTracks.length > 0 ? <RotateCcw className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
            onClick={handleRunDetection}
            disabled={!sourceVideo?.uploadId}
          >
            {detectedTracks.length > 0 ? 'Re-scan Faces' : 'Detect Faces in Footage'}
          </Button>
        )}
      </div>

      {/* Loading & Processing State */}
      {isDetecting && (
        <div className="bg-[#151520] border border-[#D6AD65]/30 rounded-2xl p-6 text-center space-y-4 animate-pulse">
          <div className="flex items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 text-[#D6AD65] animate-spin" />
            <span className="text-sm font-cinematic font-semibold text-white tracking-wider">
              {currentStage}
            </span>
          </div>

          <div className="max-w-md mx-auto grid grid-cols-3 gap-2 text-[11px] font-mono text-[#A1A1AA]">
            <div className="bg-[#1C1C28] p-2 rounded-lg border border-[#2A2A3C]">
              1. Frame Sampling
            </div>
            <div className="bg-[#1C1C28] p-2 rounded-lg border border-[#2A2A3C]">
              2. YuNet Inference
            </div>
            <div className="bg-[#1C1C28] p-2 rounded-lg border border-[#2A2A3C]">
              3. IoU Clustering
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && !isDetecting && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-500/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-2 flex-1">
            <h4 className="text-xs font-semibold text-red-300">Face Detection Error</h4>
            <p className="text-xs text-red-200/80">{error}</p>
            <Button size="sm" variant="ghost" onClick={handleRunDetection}>
              Try Again
            </Button>
          </div>
        </div>
      )}

      {/* Empty State: Scanned but 0 faces detected */}
      {hasScanned && !isDetecting && detectedTracks.length === 0 && !error && (
        <div className="p-6 rounded-2xl bg-[#171722] border border-[#2B2B3C] text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-[#D6AD65] mx-auto opacity-80" />
          <h4 className="text-sm font-cinematic font-bold text-white">
            No Human Faces Detected in Footage
          </h4>
          <p className="text-xs text-[#A1A1AA] max-w-lg mx-auto">
            OpenCV YuNet did not locate any facial boundaries exceeding the 0.60 confidence threshold in this clip.
            Please ensure the video contains visible human actors with standard framing.
          </p>
          <Button size="sm" variant="secondary" onClick={handleRunDetection}>
            Retry Detection
          </Button>
        </div>
      )}

      {/* Detected Tracks Gallery */}
      {detectedTracks.length > 0 && !isDetecting && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-[#A1A1AA]">
              Candidate Actor Tracks ({detectedTracks.length} Found) — Choose Actor to Replace:
            </span>
            <span className="text-xs text-[#D6AD65] font-mono">
              {selectedTrackId ? `Selected: ${selectedTrackId}` : 'None Selected'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {detectedTracks.map((track) => {
              const isSelected = selectedTrackId === track.trackId;
              const thumbUrl = resolveThumbnailUrl(track);

              return (
                <div
                  key={track.trackId}
                  onClick={() => handleSelectTrack(track.trackId)}
                  className={`group relative rounded-2xl p-4 transition-all duration-300 cursor-pointer border flex flex-col justify-between ${
                    isSelected
                      ? 'bg-[#1C1814] border-[#D6AD65] shadow-[0_0_20px_rgba(214,173,101,0.25)]'
                      : 'bg-[#14141C] border-[#252535] hover:border-[#8E3048]/60 hover:bg-[#181824]'
                  }`}
                >
                  {/* Selected check badge */}
                  {isSelected && (
                    <div className="absolute top-3 right-3 bg-[#D6AD65] text-[#09090B] rounded-full p-1 shadow-md z-10">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  )}

                  <div className="space-y-3">
                    {/* Cropped Face Thumbnail */}
                    <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-[#0A0A0E] border border-[#282838] flex items-center justify-center">
                      {thumbUrl ? (
                        <img
                          src={thumbUrl}
                          alt={track.label}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          onError={(e) => {
                            // Fallback if local blob URL or server link fails
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      ) : (
                        <UserCheck className="w-12 h-12 text-[#606070]" />
                      )}

                      {/* Bounding box badge */}
                      <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/75 backdrop-blur-md text-[10px] font-mono text-[#E4E4E7]">
                        {track.boundingBox.width}x{track.boundingBox.height} px
                      </div>
                    </div>

                    {/* Actor Details */}
                    <div>
                      <h4 className="text-sm font-cinematic font-bold text-white flex items-center gap-1.5">
                        {track.label}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[11px] font-mono text-emerald-400">
                          {Math.round(track.confidence * 100)}% Confidence
                        </span>
                        <span className="text-[#52525B] text-xs">•</span>
                        <span className="text-[11px] text-[#A1A1AA] flex items-center gap-1">
                          <Video className="w-3 h-3 text-[#A1A1AA]" />
                          {track.occurrences} {track.occurrences === 1 ? 'frame' : 'frames'}
                        </span>
                      </div>
                    </div>

                    {/* Timestamps appearances */}
                    {track.timestamps && track.timestamps.length > 0 && (
                      <div className="pt-2 border-t border-[#222230] flex items-center gap-1.5 flex-wrap">
                        <Clock className="w-3 h-3 text-[#71717A] shrink-0" />
                        <span className="text-[10px] font-mono text-[#71717A]">Timestamps:</span>
                        {track.timestamps.slice(0, 4).map((ts, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.5 rounded bg-[#1F1F2C] text-[10px] font-mono text-[#D4D4D8]"
                          >
                            {ts.toFixed(1)}s
                          </span>
                        ))}
                        {track.timestamps.length > 4 && (
                          <span className="text-[10px] text-[#71717A]">
                            +{track.timestamps.length - 4} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Radio Selection Action Button */}
                  <div className="mt-4 pt-3 border-t border-[#222230]">
                    <div
                      className={`w-full py-1.5 px-3 rounded-lg text-xs font-semibold text-center transition-colors flex items-center justify-center gap-1.5 ${
                        isSelected
                          ? 'bg-[#D6AD65] text-[#09090B]'
                          : 'bg-[#222230] text-[#A1A1AA] group-hover:text-white'
                      }`}
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      {isSelected ? 'Target Actor to Replace' : 'Select for Replacement'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Phase 4 Integrity Notice */}
          <div className="p-3 rounded-xl bg-[#12121A] border border-[#20202E] flex items-center gap-2.5 text-xs text-[#A1A1AA]">
            <ShieldCheck className="w-4 h-4 text-[#D6AD65] shrink-0" />
            <span>
              Real OpenCV YuNet face detection & tracking hypotheses. The neural face swapping and latent blending pipeline will execute in Phase 5.
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

