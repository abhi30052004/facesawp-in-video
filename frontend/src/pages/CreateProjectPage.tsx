import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Sliders,
  Check,
} from 'lucide-react';
import { VideoUploadPanel } from '../components/wizard/VideoUploadPanel';
import { FaceSelectionPanel } from '../components/wizard/FaceSelectionPanel';
import { ActorTrackSelectionPanel } from '../components/wizard/ActorTrackSelectionPanel';
import { ConsentGateModal } from '../components/wizard/ConsentGateModal';
import { ProcessingStageView } from '../components/wizard/ProcessingStageView';
import { ResultsComparisonView } from '../components/wizard/ResultsComparisonView';
import { DetectedActorTrack, FaceSwapProject, TargetFaceSelection, VideoMetadata } from '../types/project';
import { useProjects } from '../context/ProjectContext';
import { Button } from '../components/common/Button';
import { bollySwapApi } from '../services/api';

type WizardStep = 'video' | 'face' | 'processing' | 'results';

export const CreateProjectPage: React.FC = () => {
  const navigate = useNavigate();
  const { wizardDraft, updateWizardDraft, saveCurrentProject, deductCreditForRender } = useProjects();

  const initialStep: WizardStep =
    wizardDraft.step === 'video' || wizardDraft.step === 'face' || wizardDraft.step === 'processing' || wizardDraft.step === 'results'
      ? wizardDraft.step
      : 'video';
  const [currentStep, setCurrentStep] = useState<WizardStep>(initialStep);
  const [projectTitle, setProjectTitle] = useState(wizardDraft.title || 'Face Swap Project');
  const [sourceVideo, setSourceVideo] = useState<VideoMetadata | undefined>(wizardDraft.sourceVideo);
  const [targetFace, setTargetFace] = useState<TargetFaceSelection | undefined>(wizardDraft.targetFace);
  const [detectedTracks, setDetectedTracks] = useState<DetectedActorTrack[]>(wizardDraft.detectedTracks || []);
  const [selectedActorTrackId, setSelectedActorTrackId] = useState<string | undefined>(wizardDraft.selectedActorTrackId);
  const [activeProjectId] = useState<string>(() => wizardDraft.activeProjectId || `proj_${Date.now()}`);

  const [isConsentModalOpen, setIsConsentModalOpen] = useState(false);
  const [showConfigDrawer, setShowConfigDrawer] = useState(false);
  const [backendJobData, setBackendJobData] = useState<any>(null);
  const [outputVideoUrl, setOutputVideoUrl] = useState<string | undefined>(undefined);

  // Pipeline Configuration
  const [config, setConfig] = useState({
    faceEnhance: true,
    colorHarmony: true,
    temporalConsistency: true,
    resolutionTarget: '1080p' as '720p' | '1080p' | '4k',
    cinematicGrade: 'authentic' as 'authentic' | 'warm-vintage' | 'vibrant-masala' | 'moody-noir',
    watermarkEnabled: true,
  });

  const canProceedToFace = !!sourceVideo;
  const canLaunchProcess = !!sourceVideo && !!targetFace;

  const handleConsentConfirmed = async () => {
    setIsConsentModalOpen(false);
    deductCreditForRender();

    try {
      const proj = await bollySwapApi.createProject({
        projectId: activeProjectId,
        title: projectTitle,
        originalVideoId: sourceVideo?.uploadId || 'vid_sample_source',
        replacementFaceId: targetFace?.id || 'face_sample_target',
        consentConfirmed: true,
      });

      try {
        const swapJob = await bollySwapApi.createSwapJob({
          projectId: proj?.projectId || activeProjectId,
          title: projectTitle,
          sourceVideoId: sourceVideo?.uploadId || 'vid_sample_source',
          targetFaceId: targetFace?.id || 'face_sample_target',
          targetFaceType: 'upload',
          config,
          consentConfirmed: true,
          selectedActorTrackId: selectedActorTrackId || 'track_1',
        });
        setBackendJobData(swapJob || proj?.activeJob || null);
      } catch {
        setBackendJobData(proj?.activeJob || null);
      }
    } catch (e) {
      console.warn('Backend project creation skipped or failed:', e);
    }

    setCurrentStep('processing');
  };

  const handleProcessingComplete = (outUrl?: string) => {
    if (outUrl) {
      setOutputVideoUrl(outUrl);
    }
    setCurrentStep('results');
  };

  const handleSaveToProjects = () => {
    const newProject: FaceSwapProject = {
      id: `proj-${Date.now()}`,
      title: projectTitle,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'completed',
      sourceVideo,
      targetFace,
      result: {
        outputVideoUrl:
          outputVideoUrl ||
          sourceVideo?.url ||
          'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
        thumbnailUrl:
          targetFace?.previewUrl ||
          'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80',
        resolution: `${config.resolutionTarget.toUpperCase()}`,
        renderDurationSec: 14.2,
        framesProcessed: 450,
        fps: 30,
        modelIdentifier: 'FaceSwap-NeuralBlend',
        isDemoSimulation: true,
        watermarked: config.watermarkEnabled,
        checksum: `sha256-${Math.random().toString(36).substring(2, 10)}`,
      },
    };
    saveCurrentProject(newProject);
  };

  const handleReset = () => {
    setSourceVideo(undefined);
    setTargetFace(undefined);
    setDetectedTracks([]);
    setSelectedActorTrackId(undefined);
    updateWizardDraft({
      sourceVideo: undefined,
      targetFace: undefined,
      detectedTracks: [],
      selectedActorTrackId: undefined,
      step: 'video',
    });
    setCurrentStep('video');
  };

  return (
    <div className="space-y-8 pb-16 max-w-5xl mx-auto">
      {/* Wizard Steps Stepper */}
      <div
        className="rounded-2xl p-4 sm:p-5 border transition-colors duration-200"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-card)',
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Step markers */}
          <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto pb-2 sm:pb-0">
            {/* Step 1 */}
            <div
              onClick={() => {
                if (currentStep !== 'processing') setCurrentStep('video');
              }}
              className="flex items-center gap-2.5 cursor-pointer transition-colors"
              style={{
                color: currentStep === 'video' ? 'var(--gold)' : 'var(--text-muted)',
              }}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  sourceVideo
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentStep === 'video'
                    ? 'bg-[#D6AD65] text-[#09090B]'
                    : 'bg-black/10 dark:bg-[#22222E] text-[var(--text-muted)]'
                }`}
              >
                {sourceVideo ? <Check className="w-4 h-4" /> : '1'}
              </div>
              <span className="text-xs font-medium whitespace-nowrap">Source Video</span>
            </div>

            <div className="w-6 h-[1px] bg-[var(--border)] shrink-0" />

            {/* Step 2 */}
            <div
              onClick={() => {
                if (canProceedToFace && currentStep !== 'processing') setCurrentStep('face');
              }}
              className={`flex items-center gap-2.5 transition-colors ${
                !canProceedToFace ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
              }`}
              style={{
                color: currentStep === 'face' ? 'var(--gold)' : 'var(--text-muted)',
              }}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  targetFace
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentStep === 'face'
                    ? 'bg-[#D6AD65] text-[#09090B]'
                    : 'bg-black/10 dark:bg-[#22222E] text-[var(--text-muted)]'
                }`}
              >
                {targetFace ? <Check className="w-4 h-4" /> : '2'}
              </div>
              <span className="text-xs font-medium whitespace-nowrap">Target Face</span>
            </div>

            <div className="w-6 h-[1px] bg-[var(--border)] shrink-0" />

            {/* Step 3: Processing & Results */}
            <div
              className="flex items-center gap-2.5"
              style={{
                color: currentStep === 'processing' || currentStep === 'results' ? 'var(--gold)' : 'var(--text-muted)',
              }}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  currentStep === 'results'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentStep === 'processing'
                    ? 'bg-[#D6AD65] text-[#09090B] animate-pulse'
                    : 'bg-black/10 dark:bg-[#22222E] text-[var(--text-muted)]'
                }`}
              >
                3
              </div>
              <span className="text-xs font-medium whitespace-nowrap">Process & Export</span>
            </div>
          </div>

          {/* Settings Drawer Toggle */}
          <button
            onClick={() => setShowConfigDrawer(!showConfigDrawer)}
            className="flex items-center gap-2 text-xs font-medium cursor-pointer transition-colors self-end sm:self-auto hover:opacity-80"
            style={{ color: 'var(--text-muted)' }}
          >
            <Sliders className="w-4 h-4 text-[#D6AD65]" />
            <span>Pipeline Settings</span>
          </button>
        </div>

        {/* Collapsible Pipeline Settings Panel */}
        {showConfigDrawer && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs" style={{ borderColor: 'var(--border)' }}>
            {/* Resolution Target */}
            <div className="space-y-1">
              <label className="font-mono block" style={{ color: 'var(--text-secondary)' }}>Target Resolution</label>
              <select
                value={config.resolutionTarget}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    resolutionTarget: e.target.value as '720p' | '1080p' | '4k',
                  }))
                }
                className="w-full rounded-lg px-3 py-1.5 focus:outline-none transition-colors border"
                style={{
                  backgroundColor: 'var(--bg-input)',
                  borderColor: 'var(--border)',
                  color: 'var(--text-primary)',
                }}
              >
                <option value="720p">720p HD</option>
                <option value="1080p">1080p Full HD (Default)</option>
                <option value="4k">4K Ultra HD</option>
              </select>
            </div>

            {/* Toggles */}
            <div className="space-y-2 flex flex-col justify-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.faceEnhance}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, faceEnhance: e.target.checked }))
                  }
                  className="rounded text-[#D6AD65]"
                />
                <span style={{ color: 'var(--text-primary)' }}>Face Texture Enhancement</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.temporalConsistency}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, temporalConsistency: e.target.checked }))
                  }
                  className="rounded text-[#D6AD65]"
                />
                <span style={{ color: 'var(--text-primary)' }}>Temporal Consistency</span>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Editable Project Title */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-mono uppercase shrink-0" style={{ color: 'var(--text-muted)' }}>Project Name:</label>
        <input
          type="text"
          value={projectTitle}
          onChange={(e) => setProjectTitle(e.target.value)}
          className="bg-transparent border-b hover:border-[#D6AD65] focus:border-[#D6AD65] text-base sm:text-lg font-cinematic font-bold px-1 py-0.5 focus:outline-none transition-colors flex-1"
          style={{
            borderColor: 'var(--border)',
            color: 'var(--text-primary)',
          }}
        />
      </div>

      {/* Main Step Render Container */}
      <div
        className="rounded-3xl p-6 sm:p-8 cinema-card-glow relative border transition-colors duration-200"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-card)',
        }}
      >
        {currentStep === 'video' && (
          <div className="space-y-6">
            <VideoUploadPanel
              currentVideo={sourceVideo}
              onVideoSelected={(video) => {
                setSourceVideo(video);
                updateWizardDraft({
                  sourceVideo: video,
                  activeProjectId,
                });
              }}
              onClearVideo={() => {
                setSourceVideo(undefined);
                setDetectedTracks([]);
                setSelectedActorTrackId(undefined);
                updateWizardDraft({
                  sourceVideo: undefined,
                  detectedTracks: [],
                  selectedActorTrackId: undefined,
                });
              }}
            />

            {/* Face Detection Panel */}
            {sourceVideo && (
              <ActorTrackSelectionPanel
                projectId={activeProjectId}
                sourceVideo={sourceVideo}
                detectedTracks={detectedTracks}
                selectedTrackId={selectedActorTrackId}
                onTracksDetected={(tracks, defaultId) => {
                  setDetectedTracks(tracks);
                  if (defaultId) setSelectedActorTrackId(defaultId);
                  updateWizardDraft({
                    detectedTracks: tracks,
                    selectedActorTrackId: defaultId,
                  });
                }}
                onTrackSelected={(trackId) => {
                  setSelectedActorTrackId(trackId);
                  updateWizardDraft({ selectedActorTrackId: trackId });
                }}
              />
            )}

            {/* Step navigation bottom bar */}
            <div className="pt-4 border-t flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
              <Button size="sm" variant="ghost" onClick={() => navigate('/')}>
                Cancel
              </Button>
              <Button
                size="md"
                variant="primary"
                disabled={!canProceedToFace}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => setCurrentStep('face')}
              >
                Next: Select Target Face
              </Button>
            </div>
          </div>
        )}

        {currentStep === 'face' && (
          <div className="space-y-6">
            <FaceSelectionPanel
              selectedFace={targetFace}
              onFaceSelected={(face) => {
                setTargetFace(face);
                updateWizardDraft({ targetFace: face });
              }}
            />

            {/* Step navigation bottom bar */}
            <div className="pt-4 border-t flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
              <Button
                size="sm"
                variant="secondary"
                leftIcon={<ArrowLeft className="w-4 h-4" />}
                onClick={() => setCurrentStep('video')}
              >
                Back: Source Video
              </Button>

              <Button
                size="md"
                variant="burgundy"
                disabled={!canLaunchProcess}
                leftIcon={<Sparkles className="w-4 h-4" />}
                onClick={() => setIsConsentModalOpen(true)}
              >
                Proceed to Likeness Consent & Swap
              </Button>
            </div>
          </div>
        )}

        {currentStep === 'processing' && (
          <ProcessingStageView
            sourceVideo={sourceVideo}
            targetFace={targetFace}
            activeJob={backendJobData}
            onProcessingComplete={handleProcessingComplete}
          />
        )}

        {currentStep === 'results' && (
          <ResultsComparisonView
            sourceVideo={sourceVideo}
            targetFace={targetFace}
            outputVideoUrl={outputVideoUrl}
            onReset={handleReset}
            onSaveToProjects={handleSaveToProjects}
          />
        )}
      </div>

      {/* Consent Gate Confirmation Modal */}
      <ConsentGateModal
        isOpen={isConsentModalOpen}
        onClose={() => setIsConsentModalOpen(false)}
        onConfirmConsent={handleConsentConfirmed}
      />
    </div>
  );
};
