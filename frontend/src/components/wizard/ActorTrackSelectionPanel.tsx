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
    setCurrentStage('Initializing face detection...');

    try {
      setCurrentStage('Sampling video frames...');
      const result = await bollySwapApi.detectFaces(projectId, sourceVideo.uploadId);

      setHasScanned(true);
      setCurrentStage('Analysis complete.');

      const tracks = result.tracks || [];
      const defaultId = result.selectedTrackId || (tracks.length > 0 ? tracks[0].trackId : undefined);
      onTracksDetected(tracks, defaultId);
    } catch (err: any) {
      setError(
        err?.message ||
          'Face detection failed. Ensure the video contains readable face frames.'
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
      console.warn('Track selection persistence skipped or pending:', err);
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
    <div className="space-y-6 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
      {/* Header with Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Scan className="w-5 h-5 text-[#D6AD65]" />
            <h3
              className="text-base sm:text-lg font-cinematic font-bold tracking-wide"
              style={{ color: 'var(--text-primary)' }}
            >
              Detected Faces in Video
            </h3>
          </div>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            Detect faces in the footage to choose which person you want to swap.
          </p>
        </div>

        {!hasScanned && (
          <Button
            size="sm"
            variant="primary"
            isLoading={isDetecting}
            leftIcon={<Scan className="w-4 h-4" />}
            onClick={handleRunDetection}
          >
            Scan Faces
          </Button>
        )}

        {hasScanned && (
          <Button
            size="sm"
            variant="outline"
            isLoading={isDetecting}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
            onClick={handleRunDetection}
          >
            Re-scan Faces
          </Button>
        )}
      </div>

      {/* Loading & Processing State */}
      {isDetecting && (
        <div
          className="border rounded-2xl p-6 text-center space-y-4 animate-pulse"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--gold)',
          }}
        >
          <div className="flex items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 text-[#D6AD65] animate-spin" />
            <span className="text-sm font-cinematic font-semibold tracking-wider" style={{ color: 'var(--text-primary)' }}>
              {currentStage}
            </span>
          </div>

          <div className="max-w-md mx-auto grid grid-cols-3 gap-2 text-[11px] font-mono" style={{ color: 'var(--text-secondary)' }}>
            <div className="p-2 rounded-lg border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              1. Frame Sampling
            </div>
            <div className="p-2 rounded-lg border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              2. Face Detection
            </div>
            <div className="p-2 rounded-lg border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              3. Track Clustering
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
        <div
          className="p-6 rounded-2xl border text-center space-y-3"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
          }}
        >
          <AlertCircle className="w-8 h-8 text-[#D6AD65] mx-auto opacity-80" />
          <h4 className="text-sm font-cinematic font-bold" style={{ color: 'var(--text-primary)' }}>
            No Faces Detected
          </h4>
          <p className="text-xs max-w-lg mx-auto" style={{ color: 'var(--text-faint)' }}>
            No clear facial boundaries were detected in this clip. Ensure the video contains visible human faces with clear lighting.
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
            <span className="text-xs font-mono uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Detected Faces ({detectedTracks.length} Found) — Choose who to replace:
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
                  className="group relative rounded-2xl p-4 transition-all duration-300 cursor-pointer border flex flex-col justify-between"
                  style={{
                    backgroundColor: isSelected ? 'rgba(214, 173, 101, 0.12)' : 'var(--bg-input)',
                    borderColor: isSelected ? 'var(--gold)' : 'var(--border)',
                  }}
                >
                  {/* Selected check badge */}
                  {isSelected && (
                    <div className="absolute top-3 right-3 bg-[#D6AD65] text-[#09090B] rounded-full p-1 shadow-md z-10">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  )}

                  <div className="space-y-3">
                    {/* Face Thumbnail */}
                    <div
                      className="relative aspect-square w-full rounded-xl overflow-hidden border flex items-center justify-center bg-black/5 dark:bg-[#0A0A0E]"
                      style={{ borderColor: 'var(--border)' }}
                    >
                      {thumbUrl ? (
                        <img
                          src={thumbUrl}
                          alt={track.label}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          onError={(e) => {
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
                      <h4 className="text-sm font-cinematic font-bold flex items-center gap-1.5" style={{ color: 'var(--text-primary)' }}>
                        {track.label}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[11px] font-mono text-emerald-500">
                          {Math.round(track.confidence * 100)}% Confidence
                        </span>
                        <span className="text-[11px] flex items-center gap-1" style={{ color: 'var(--text-faint)' }}>
                          • {track.occurrences} {track.occurrences === 1 ? 'frame' : 'frames'}
                        </span>
                      </div>
                    </div>

                    {/* Timestamps appearances */}
                    {track.timestamps && track.timestamps.length > 0 && (
                      <div className="pt-2 border-t flex items-center gap-1.5 flex-wrap" style={{ borderColor: 'var(--border)' }}>
                        <Clock className="w-3 h-3 text-[#71717A] shrink-0" />
                        <span className="text-[10px] font-mono text-[#71717A]">Times:</span>
                        {track.timestamps.slice(0, 4).map((ts, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.5 rounded text-[10px] font-mono border"
                            style={{
                              backgroundColor: 'var(--bg-card)',
                              borderColor: 'var(--border)',
                              color: 'var(--text-secondary)',
                            }}
                          >
                            {ts.toFixed(1)}s
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Radio Selection Action Button */}
                  <div className="mt-4 pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
                    <div
                      className="w-full py-1.5 px-3 rounded-lg text-xs font-semibold text-center transition-colors flex items-center justify-center gap-1.5"
                      style={{
                        backgroundColor: isSelected ? 'var(--gold)' : 'var(--bg-card)',
                        color: isSelected ? '#09090B' : 'var(--text-secondary)',
                      }}
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      {isSelected ? 'Selected Face' : 'Select Face'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
