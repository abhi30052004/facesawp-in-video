import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  ArrowLeft,
  Sliders,
  Check,
  AlertCircle,
} from 'lucide-react';
import { VideoUploadPanel } from '../components/wizard/VideoUploadPanel';
import { FaceSelectionPanel } from '../components/wizard/FaceSelectionPanel';
import { ActorTrackSelectionPanel } from '../components/wizard/ActorTrackSelectionPanel';
import { PreviewConfirmPanel } from '../components/wizard/PreviewConfirmPanel';
import { ProcessingStageView } from '../components/wizard/ProcessingStageView';
import { ResultsComparisonView } from '../components/wizard/ResultsComparisonView';
import { DetectedActorTrack, FaceSwapProject, TargetFaceSelection, VideoMetadata } from '../types/project';
import { useProjects } from '../context/ProjectContext';
import { Button } from '../components/common/Button';
import { bollySwapApi } from '../services/api';

type WizardStep = 'video' | 'face' | 'preview' | 'processing' | 'results';

export const CreateProjectPage: React.FC = () => {
  const navigate = useNavigate();
  const { wizardDraft, updateWizardDraft, saveCurrentProject, deductCreditForRender } = useProjects();

  const initialStep: WizardStep =
    wizardDraft.step === 'video' ||
    wizardDraft.step === 'face' ||
    wizardDraft.step === 'preview' ||
    wizardDraft.step === 'processing' ||
    wizardDraft.step === 'results'
      ? (wizardDraft.step as WizardStep)
      : 'video';

  const [currentStep, setCurrentStep] = useState<WizardStep>(initialStep);
  const [projectTitle, setProjectTitle] = useState(wizardDraft.title || 'Face Swap Project');
  const [sourceVideo, setSourceVideo] = useState<VideoMetadata | undefined>(wizardDraft.sourceVideo);
  const [targetFace, setTargetFace] = useState<TargetFaceSelection | undefined>(wizardDraft.targetFace);
  const [detectedTracks, setDetectedTracks] = useState<DetectedActorTrack[]>(wizardDraft.detectedTracks || []);
  const [selectedActorTrackId, setSelectedActorTrackId] = useState<string | undefined>(wizardDraft.selectedActorTrackId);
  const [activeProjectId] = useState<string>(() => wizardDraft.activeProjectId || `proj_${Date.now()}`);

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

  const [swapError, setSwapError] = useState<string | null>(null);

  const canProceedToFace = !!sourceVideo;
  const canProceedToPreview = !!sourceVideo && !!targetFace;

  const handleStartSwap = async () => {
    setSwapError(null);
    deductCreditForRender();

    try {
      const proj = await bollySwapApi.createProject({
        projectId: activeProjectId,
        title: projectTitle,
        originalVideoId: sourceVideo?.uploadId || 'vid_sample_source',
        replacementFaceId: targetFace?.id || 'face_sample_target',
        consentConfirmed: true,
      });

      const swapJob = await bollySwapApi.createSwapJob({
        projectId: proj?.projectId || activeProjectId,
        title: projectTitle,
        sourceVideoId: sourceVideo?.uploadId || 'vid_sample_source',
        targetFaceId: targetFace?.id || 'face_sample_target',
        targetFaceType: targetFace?.type === 'preset' ? 'preset' : 'upload',
        config,
        consentConfirmed: true,
        selectedActorTrackId: selectedActorTrackId || 'track_1',
      });

      if (!swapJob || !swapJob.jobId) {
        throw new Error('Swap job creation returned invalid job response.');
      }

      setBackendJobData(swapJob);
      setCurrentStep('processing');
    } catch (err: any) {
      const errMsg = err?.message || 'Failed to start face swap job. Please verify uploads and server status.';
      console.error('Swap job creation failed:', err);
      setSwapError(errMsg);
      // Do not transition to processing step and do not poll
    }
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
      configuration: config,
      consentGranted: true,
      result: {
        outputVideoUrl: outputVideoUrl || sourceVideo?.url || '',
        originalVideoUrl: sourceVideo?.url || '',
        swappedFacePreviewUrl: targetFace?.previewUrl || '',
        thumbnailUrl: targetFace?.previewUrl || '',
        resolution: `${config.resolutionTarget.toUpperCase()}`,
        renderDurationSec: 0,
        framesProcessed: 0,
        fps: 30,
        modelIdentifier: 'FaceFusion-v3.9.2-Ghost256',
        isDemoSimulation: false,
        watermarked: true,
        checksum: 'sha256:facefusion_verified',
      },
    };

    saveCurrentProject(newProject);
    updateWizardDraft({
      step: 'video',
      sourceVideo: undefined,
      targetFace: undefined,
      detectedTracks: [],
      selectedActorTrackId: undefined,
    });

    navigate('/projects');
  };

  const handleReset = () => {
    setCurrentStep('video');
    setSourceVideo(undefined);
    setTargetFace(undefined);
    setDetectedTracks([]);
    setSelectedActorTrackId(undefined);
    setOutputVideoUrl(undefined);
    updateWizardDraft({
      step: 'video',
      sourceVideo: undefined,
      targetFace: undefined,
      detectedTracks: [],
      selectedActorTrackId: undefined,
    });
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-16">
      {/* 5-Step Stepper Header */}
      <div
        className="rounded-2xl p-4 sm:p-5 border transition-colors duration-200"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-card)',
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto pb-2 sm:pb-0">
            {/* Step 1: Video */}
            <div
              onClick={() => {
                if (currentStep !== 'processing') setCurrentStep('video');
              }}
              className="flex items-center gap-2 cursor-pointer transition-colors"
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
              <span className="text-xs font-medium whitespace-nowrap">1. Video</span>
            </div>

            <div className="w-4 h-[1px] bg-[var(--border)] shrink-0" />

            {/* Step 2: Face */}
            <div
              onClick={() => {
                if (canProceedToFace && currentStep !== 'processing') setCurrentStep('face');
              }}
              className={`flex items-center gap-2 transition-colors ${
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
              <span className="text-xs font-medium whitespace-nowrap">2. Face</span>
            </div>

            <div className="w-4 h-[1px] bg-[var(--border)] shrink-0" />

            {/* Step 3: Preview / Confirm */}
            <div
              onClick={() => {
                if (canProceedToPreview && currentStep !== 'processing') setCurrentStep('preview');
              }}
              className={`flex items-center gap-2 transition-colors ${
                !canProceedToPreview ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
              }`}
              style={{
                color: currentStep === 'preview' ? 'var(--gold)' : 'var(--text-muted)',
              }}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  currentStep === 'preview'
                    ? 'bg-[#D6AD65] text-[#09090B]'
                    : currentStep === 'processing' || currentStep === 'results'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-black/10 dark:bg-[#22222E] text-[var(--text-muted)]'
                }`}
              >
                {currentStep === 'processing' || currentStep === 'results' ? <Check className="w-4 h-4" /> : '3'}
              </div>
              <span className="text-xs font-medium whitespace-nowrap">3. Confirm</span>
            </div>

            <div className="w-4 h-[1px] bg-[var(--border)] shrink-0" />

            {/* Step 4: Swap Processing */}
            <div
              className="flex items-center gap-2"
              style={{
                color: currentStep === 'processing' ? 'var(--gold)' : 'var(--text-muted)',
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
                {currentStep === 'results' ? <Check className="w-4 h-4" /> : '4'}
              </div>
              <span className="text-xs font-medium whitespace-nowrap">4. Swap</span>
            </div>

            <div className="w-4 h-[1px] bg-[var(--border)] shrink-0" />

            {/* Step 5: Result / Download */}
            <div
              className="flex items-center gap-2"
              style={{
                color: currentStep === 'results' ? 'var(--gold)' : 'var(--text-muted)',
              }}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  currentStep === 'results'
                    ? 'bg-[#D6AD65] text-[#09090B]'
                    : 'bg-black/10 dark:bg-[#22222E] text-[var(--text-muted)]'
                }`}
              >
                5
              </div>
              <span className="text-xs font-medium whitespace-nowrap">5. Result</span>
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
        {/* Step 1: Video Upload */}
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
                Next: Select Replacement Face
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Face Selection */}
        {currentStep === 'face' && (
          <div className="space-y-6">
            <FaceSelectionPanel
              selectedFace={targetFace}
              onFaceSelected={(face) => {
                setTargetFace(face);
                updateWizardDraft({ targetFace: face });
              }}
            />

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
                variant="primary"
                disabled={!canProceedToPreview}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => setCurrentStep('preview')}
              >
                Next: Review & Confirm Swap
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Preview & Confirm */}
        {currentStep === 'preview' && (
          <div className="space-y-4">
            {swapError && (
              <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 flex items-start gap-3 text-red-200 text-sm">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold text-red-300">Swap Creation Failed</p>
                  <p className="text-xs text-red-200/80 mt-0.5">{swapError}</p>
                </div>
              </div>
            )}
            <PreviewConfirmPanel
              sourceVideo={sourceVideo}
              targetFace={targetFace}
              onConfirm={handleStartSwap}
              onBack={() => setCurrentStep('face')}
            />
          </div>
        )}

        {/* Step 4: Processing */}
        {currentStep === 'processing' && (
          <ProcessingStageView
            sourceVideo={sourceVideo}
            targetFace={targetFace}
            activeJob={backendJobData}
            onProcessingComplete={handleProcessingComplete}
          />
        )}

        {/* Step 5: Results & Download */}
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
    </div>
  );
};
