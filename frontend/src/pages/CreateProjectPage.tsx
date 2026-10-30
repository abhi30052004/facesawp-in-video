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
  const [projectTitle, setProjectTitle] = useState(wizardDraft.title || 'Monsoon Soliloquy Re-enactment');
  const [sourceVideo, setSourceVideo] = useState<VideoMetadata | undefined>(wizardDraft.sourceVideo);
  const [targetFace, setTargetFace] = useState<TargetFaceSelection | undefined>(wizardDraft.targetFace);
  const [detectedTracks, setDetectedTracks] = useState<DetectedActorTrack[]>(wizardDraft.detectedTracks || []);
  const [selectedActorTrackId, setSelectedActorTrackId] = useState<string | undefined>(wizardDraft.selectedActorTrackId);
  const [activeProjectId] = useState<string>(() => wizardDraft.activeProjectId || `proj_${Date.now()}`);

  const [isConsentModalOpen, setIsConsentModalOpen] = useState(false);
  const [showConfigDrawer, setShowConfigDrawer] = useState(false);
  const [backendJobData, setBackendJobData] = useState<any>(null);

  // Studio Pipeline Configuration
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
        title: projectTitle,
        originalVideoId: sourceVideo?.uploadId || 'vid_sample_source',
        replacementFaceId: targetFace?.id || 'face_sample_target',
        consentConfirmed: true,
      });
      setBackendJobData(proj?.activeJob || null);
    } catch (e) {
      console.warn('Backend project creation skipped or failed:', e);
    }

    setCurrentStep('processing');
  };

  const handleProcessingComplete = () => {
    setCurrentStep('results');
  };

  const handleSaveToProjects = () => {
    const newProject: FaceSwapProject = {
      id: `proj-${Date.now()}`,
      title: projectTitle,
      status: 'completed',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      sourceVideo,
      targetFace,
      detectedTracks,
      selectedActorTrackId,
      configuration: config,
      consentGranted: true,
      consentTimestamp: new Date().toISOString(),
      result: {
        outputVideoUrl:
          sourceVideo?.url ||
          'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
        originalVideoUrl:
          sourceVideo?.url ||
          'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
        swappedFacePreviewUrl:
          targetFace?.previewUrl ||
          'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80',
        resolution: `${config.resolutionTarget.toUpperCase()} Cinematic`,
        renderDurationSec: 14.2,
        framesProcessed: 450,
        fps: 30,
        modelIdentifier: 'BollyMesh-v2.4-NeuralBlend',
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
      <div className="bg-[#14141B] border border-[#242432] rounded-2xl p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Step markers */}
          <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto pb-2 sm:pb-0">
            {/* Step 1 */}
            <div
              onClick={() => {
                if (currentStep !== 'processing') setCurrentStep('video');
              }}
              className={`flex items-center gap-2.5 cursor-pointer transition-colors ${
                currentStep === 'video' ? 'text-[#D6AD65]' : 'text-[#71717A] hover:text-white'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  sourceVideo
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentStep === 'video'
                    ? 'bg-[#D6AD65] text-[#09090B]'
                    : 'bg-[#22222E] text-[#8E8E9E]'
                }`}
              >
                {sourceVideo ? <Check className="w-4 h-4" /> : '1'}
              </div>
              <span className="text-xs font-medium whitespace-nowrap">Footage Ingestion</span>
            </div>

            <div className="w-6 h-[1px] bg-[#272738] shrink-0" />

            {/* Step 2 */}
            <div
              onClick={() => {
                if (canProceedToFace && currentStep !== 'processing') setCurrentStep('face');
              }}
              className={`flex items-center gap-2.5 transition-colors ${
                !canProceedToFace
                  ? 'opacity-40 cursor-not-allowed'
                  : currentStep === 'face'
                  ? 'text-[#D6AD65] cursor-pointer'
                  : 'text-[#71717A] hover:text-white cursor-pointer'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  targetFace
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentStep === 'face'
                    ? 'bg-[#D6AD65] text-[#09090B]'
                    : 'bg-[#22222E] text-[#8E8E9E]'
                }`}
              >
                {targetFace ? <Check className="w-4 h-4" /> : '2'}
              </div>
              <span className="text-xs font-medium whitespace-nowrap">Target Identity</span>
            </div>

            <div className="w-6 h-[1px] bg-[#272738] shrink-0" />

            {/* Step 3: Processing & Results */}
            <div
              className={`flex items-center gap-2.5 ${
                currentStep === 'processing' || currentStep === 'results'
                  ? 'text-[#D6AD65]'
                  : 'text-[#71717A]'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  currentStep === 'results'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentStep === 'processing'
                    ? 'bg-[#8E3048] text-white animate-pulse'
                    : 'bg-[#22222E] text-[#8E8E9E]'
                }`}
              >
                3
              </div>
              <span className="text-xs font-medium whitespace-nowrap">Synthesis & Output</span>
            </div>
          </div>

          {/* Quick config toggle button */}
          <button
            onClick={() => setShowConfigDrawer(!showConfigDrawer)}
            className="self-end sm:self-auto px-3 py-1.5 rounded-xl bg-[#1A1A24] border border-[#2B2B3C] text-xs text-[#A1A1AA] hover:text-[#D6AD65] hover:border-[#D6AD65]/40 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Sliders className="w-3.5 h-3.5 text-[#D6AD65]" />
            <span>AI Pipeline Settings</span>
          </button>
        </div>

        {/* Collapsible Pipeline Settings Panel */}
        {showConfigDrawer && (
          <div className="mt-4 pt-4 border-t border-[#252535] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            {/* Resolution Target */}
            <div className="space-y-1">
              <label className="text-[#A1A1AA] font-mono">Render Target Resolution</label>
              <select
                value={config.resolutionTarget}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    resolutionTarget: e.target.value as '720p' | '1080p' | '4k',
                  }))
                }
                className="w-full bg-[#1A1A24] border border-[#2F2F40] rounded-lg px-3 py-1.5 text-white focus:outline-none focus:border-[#D6AD65]"
              >
                <option value="720p">720p High-Efficiency Preview</option>
                <option value="1080p">1080p Master Cinematic (Default)</option>
                <option value="4k">4K Ultra Cinema Master</option>
              </select>
            </div>

            {/* Color Grade */}
            <div className="space-y-1">
              <label className="text-[#A1A1AA] font-mono">Cinematic Color Palette</label>
              <select
                value={config.cinematicGrade}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    cinematicGrade: e.target.value as any,
                  }))
                }
                className="w-full bg-[#1A1A24] border border-[#2F2F40] rounded-lg px-3 py-1.5 text-white focus:outline-none focus:border-[#D6AD65]"
              >
                <option value="authentic">Authentic Camera Profile</option>
                <option value="warm-vintage">90s Golden Nostalgia</option>
                <option value="vibrant-masala">Vibrant Masala Extravaganza</option>
                <option value="moody-noir">Moody Neo-Noir Crime</option>
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
                  className="rounded text-[#D6AD65] bg-[#09090B] border-[#38384A]"
                />
                <span className="text-[#EDEDED]">High-Precision Face Texture Restorer</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.temporalConsistency}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, temporalConsistency: e.target.checked }))
                  }
                  className="rounded text-[#D6AD65] bg-[#09090B] border-[#38384A]"
                />
                <span className="text-[#EDEDED]">Anti-Jitter Temporal Consistency</span>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Editable Project Title */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-mono text-[#71717A] uppercase shrink-0">Project Name:</label>
        <input
          type="text"
          value={projectTitle}
          onChange={(e) => setProjectTitle(e.target.value)}
          className="bg-transparent border-b border-[#2C2C3D] hover:border-[#D6AD65] focus:border-[#D6AD65] text-white text-base sm:text-lg font-cinematic font-bold px-1 py-0.5 focus:outline-none transition-colors flex-1"
        />
      </div>

      {/* Main Step Render Container */}
      <div className="bg-[#111116] border border-[#22222E] rounded-3xl p-6 sm:p-8 cinema-card-glow relative">
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

            {/* Real OpenCV YuNet Face Detection & Actor Selection Panel */}
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
            <div className="pt-4 border-t border-[#20202C] flex items-center justify-between">
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
            <div className="pt-4 border-t border-[#20202C] flex items-center justify-between">
              <Button
                size="sm"
                variant="secondary"
                leftIcon={<ArrowLeft className="w-4 h-4" />}
                onClick={() => setCurrentStep('video')}
              >
                Back: Source Footage
              </Button>

              <Button
                size="md"
                variant="burgundy"
                disabled={!canLaunchProcess}
                leftIcon={<Sparkles className="w-4 h-4" />}
                onClick={() => setIsConsentModalOpen(true)}
              >
                Proceed to Likeness Consent & Synthesis
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
