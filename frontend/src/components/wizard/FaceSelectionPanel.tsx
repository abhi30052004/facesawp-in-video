import React, { useState, useRef } from 'react';
import { UserCheck, Upload, Sparkles, Check, AlertCircle, Info, Star, Loader2 } from 'lucide-react';
import { TargetFacePreset, TargetFaceSelection } from '../../types/project';
import { DEMO_ACTOR_PRESETS } from '../../services/mockData';
import { validateImageFile } from '../../utils/mediaValidation';
import { Badge } from '../common/Badge';
import { bollySwapApi } from '../../services/api';

interface FaceSelectionPanelProps {
  selectedFace?: TargetFaceSelection;
  onFaceSelected: (face: TargetFaceSelection) => void;
}

export const FaceSelectionPanel: React.FC<FaceSelectionPanelProps> = ({
  selectedFace,
  onFaceSelected,
}) => {
  const [activeTab, setActiveTab] = useState<'roster' | 'upload'>('roster');
  const [categoryFilter, setCategoryFilter] = useState<string>('All');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const categories = ['All', 'Romantic Era', 'Cinematic Legends', 'Action Heroes', 'Contemporary Stars'];

  const filteredPresets = categoryFilter === 'All'
    ? DEMO_ACTOR_PRESETS
    : DEMO_ACTOR_PRESETS.filter((p) => p.category === categoryFilter);

  const handleCustomImageUpload = async (file: File) => {
    setUploadError(null);
    setUploadProgress(0);

    const validation = validateImageFile(file);
    if (!validation.isValid) {
      setUploadError(validation.error || 'Invalid image file');
      setUploadProgress(null);
      return;
    }

    try {
      const uploadRes = await bollySwapApi.uploadTargetFace(file, (p) => setUploadProgress(p));
      const objectUrl = URL.createObjectURL(file);

      const customSelection: TargetFaceSelection = {
        type: 'custom',
        id: uploadRes.faceId,
        name: file.name.replace(/\.[^/.]+$/, ''),
        previewUrl: uploadRes.previewUrl || objectUrl,
        isDemo: false,
        detectedLandmarksCount: 468,
        qualityRating: 'Excellent',
      };
      onFaceSelected(customSelection);
    } catch (err: any) {
      setUploadError(err?.message || 'Face image upload failed.');
    } finally {
      setUploadProgress(null);
    }
  };

  const handlePresetSelect = (preset: TargetFacePreset) => {
    const presetSelection: TargetFaceSelection = {
      type: 'preset',
      id: preset.id,
      name: preset.name,
      previewUrl: preset.avatarUrl,
      isDemo: true,
      detectedLandmarksCount: 468,
      qualityRating: 'Excellent',
    };
    onFaceSelected(presetSelection);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2
            className="text-xl font-cinematic font-bold flex items-center gap-2"
            style={{ color: 'var(--text-primary)' }}
          >
            <UserCheck className="w-5 h-5 text-[#D6AD65]" />
            Step 2: Target Actor Identity
          </h2>
          <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
            Select an actor preset or upload a custom target face.
          </p>
        </div>

        {/* Tab switch */}
        <div
          className="flex p-1 rounded-xl self-start sm:self-auto border"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
          }}
        >
          <button
            onClick={() => setActiveTab('roster')}
            className="px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer flex items-center gap-1.5"
            style={{
              backgroundColor: activeTab === 'roster' ? 'var(--gold)' : 'transparent',
              color: activeTab === 'roster' ? '#09090B' : 'var(--text-secondary)',
              fontWeight: activeTab === 'roster' ? 600 : 500,
            }}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Actor Presets
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className="px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer flex items-center gap-1.5"
            style={{
              backgroundColor: activeTab === 'upload' ? 'var(--gold)' : 'transparent',
              color: activeTab === 'upload' ? '#09090B' : 'var(--text-secondary)',
              fontWeight: activeTab === 'upload' ? 600 : 500,
            }}
          >
            <Upload className="w-3.5 h-3.5" />
            Upload Custom Face
          </button>
        </div>
      </div>

      {/* Selected Face confirmation pill if chosen */}
      {selectedFace && (
        <div
          className="p-3.5 rounded-xl border flex items-center justify-between gap-4 transition-colors"
          style={{
            backgroundColor: 'rgba(214, 173, 101, 0.1)',
            borderColor: 'var(--gold)',
          }}
        >
          <div className="flex items-center gap-3">
            <img
              src={selectedFace.previewUrl}
              alt={selectedFace.name}
              className="w-10 h-10 rounded-lg object-cover border border-[#D6AD65]"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Selected Target: {selectedFace.name}
                </span>
                <Badge variant={selectedFace.isDemo ? 'demo' : 'emerald'}>
                  {selectedFace.isDemo ? 'Preset' : 'Custom Upload'}
                </Badge>
              </div>
              <span className="text-[11px] font-mono text-[#D6AD65]">
                Ready for alignment & neural reenactment
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-emerald-500 font-medium">
            <Check className="w-4 h-4" />
            <span>Configured</span>
          </div>
        </div>
      )}

      {/* Tab 1: Actor Roster */}
      {activeTab === 'roster' && (
        <div className="space-y-4">
          {/* Categories pill filters */}
          <div className="flex flex-wrap items-center gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className="px-3 py-1 text-xs rounded-lg border transition-all cursor-pointer"
                style={{
                  backgroundColor: categoryFilter === cat ? 'rgba(214, 173, 101, 0.15)' : 'var(--bg-input)',
                  borderColor: categoryFilter === cat ? 'var(--gold)' : 'var(--border)',
                  color: categoryFilter === cat ? 'var(--gold)' : 'var(--text-secondary)',
                  fontWeight: categoryFilter === cat ? 600 : 500,
                }}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Roster Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPresets.map((preset) => {
              const isSelected = selectedFace?.id === preset.id;
              return (
                <div
                  key={preset.id}
                  onClick={() => handlePresetSelect(preset)}
                  className="relative border rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 group hover:-translate-y-1"
                  style={{
                    backgroundColor: isSelected ? 'rgba(214, 173, 101, 0.12)' : 'var(--bg-input)',
                    borderColor: isSelected ? 'var(--gold)' : 'var(--border)',
                  }}
                >
                  {/* Actor image */}
                  <div className="relative aspect-[4/3] overflow-hidden bg-black">
                    <img
                      src={preset.avatarUrl}
                      alt={preset.name}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20" />

                    {/* Demo badge overlay */}
                    <div className="absolute top-3 left-3">
                      <Badge variant="demo">Preset</Badge>
                    </div>

                    {/* Compatibility score */}
                    <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-md px-2 py-0.5 rounded-full border border-[#D6AD65]/30 text-[11px] font-mono text-[#D6AD65] flex items-center gap-1">
                      <Star className="w-3 h-3 fill-[#D6AD65]" />
                      {preset.suitabilityScore}% Match
                    </div>

                    {/* Selected check */}
                    {isSelected && (
                      <div className="absolute bottom-3 right-3 w-7 h-7 rounded-full bg-[#D6AD65] text-[#09090B] flex items-center justify-center font-bold shadow-lg">
                        <Check className="w-4 h-4 stroke-[3]" />
                      </div>
                    )}
                  </div>

                  {/* Actor info */}
                  <div className="p-4">
                    <div className="mb-1">
                      <h4
                        className="text-base font-cinematic font-bold group-hover:text-[#D6AD65] transition-colors"
                        style={{ color: 'var(--text-primary)' }}
                      >
                        {preset.name}
                      </h4>
                      <p className="text-xs text-[#D6AD65] font-medium">{preset.title}</p>
                    </div>

                    <p className="text-xs line-clamp-2 mb-3" style={{ color: 'var(--text-faint)' }}>
                      {preset.description}
                    </p>

                    <div
                      className="pt-2.5 border-t flex items-center justify-between text-[11px]"
                      style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}
                    >
                      <span className="font-mono">{preset.era}</span>
                      <span className="text-[#D6AD65] group-hover:underline font-semibold">Select Actor →</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Custom Upload */}
      {activeTab === 'upload' && (
        <div className="space-y-4">
          {/* Error if any */}
          {uploadError && (
            <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 flex items-start gap-3 text-red-200 text-sm">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-300">Image Validation Error</p>
                <p className="text-xs text-red-200/80 mt-0.5">{uploadError}</p>
              </div>
            </div>
          )}

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all cursor-pointer group"
            style={{
              backgroundColor: 'var(--bg-input)',
              borderColor: 'var(--border)',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,image/jpeg,image/png"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleCustomImageUpload(e.target.files[0]);
                }
              }}
            />

            <div
              className="w-16 h-16 rounded-2xl border flex items-center justify-center text-[#D6AD65] mx-auto mb-4 group-hover:scale-110 transition-all shadow-sm"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderColor: 'var(--border)',
              }}
            >
              <Upload className="w-7 h-7" />
            </div>

            <h3 className="text-base font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
              Upload Front-Facing Face Portrait
            </h3>
            <p className="text-xs max-w-md mx-auto mb-4" style={{ color: 'var(--text-faint)' }}>
              Upload JPG or PNG up to 10MB. For optimal results, use an evenly-lit headshot looking directly into the camera.
            </p>

            {uploadProgress !== null ? (
              <div className="w-full max-w-xs mx-auto space-y-2 mt-2">
                <div className="flex justify-between items-center text-xs font-mono text-[#D6AD65]">
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Uploading Face Portrait...
                  </span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-[var(--border)] h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-[#D6AD65] to-[#8E3048] h-full transition-all duration-300 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="px-4 py-2 text-xs font-semibold rounded-xl border border-[#D6AD65]/40 text-[#D6AD65] hover:bg-[#D6AD65]/10 transition-colors"
              >
                Browse Image Files
              </button>
            )}
          </div>

          {/* Guidelines note */}
          <div
            className="p-3.5 rounded-xl border flex items-start gap-2.5 text-xs"
            style={{
              backgroundColor: 'var(--bg-input)',
              borderColor: 'var(--border)',
              color: 'var(--text-faint)',
            }}
          >
            <Info className="w-4 h-4 text-[#D6AD65] shrink-0 mt-0.5" />
            <p>
              <strong style={{ color: 'var(--text-primary)' }}>Quality Guidelines:</strong> Avoid heavy sunglasses, extreme head tilts, or blur. The model normalizes ambient light to match the destination footage.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
