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
          <h2 className="text-xl font-cinematic font-bold text-white flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-[#D6AD65]" />
            Step 2: Target Actor Identity
          </h2>
          <p className="text-xs sm:text-sm text-[#A1A1AA]">
            Select an iconic Bollywood archetype preset or upload a custom target face.
          </p>
        </div>

        {/* Tab switch */}
        <div className="flex p-1 bg-[#14141B] border border-[#272736] rounded-xl self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('roster')}
            className={`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'roster'
                ? 'bg-gradient-to-r from-[#D6AD65] to-[#C09848] text-[#09090B] font-semibold shadow-sm'
                : 'text-[#A1A1AA] hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Actor Roster (Demo)
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'upload'
                ? 'bg-gradient-to-r from-[#D6AD65] to-[#C09848] text-[#09090B] font-semibold shadow-sm'
                : 'text-[#A1A1AA] hover:text-white'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            Upload Custom Face
          </button>
        </div>
      </div>

      {/* Selected Face Active Banner */}
      {selectedFace && (
        <div className="p-3.5 rounded-xl bg-gradient-to-r from-[#D6AD65]/10 via-[#1B1B24] to-[#8E3048]/10 border border-[#D6AD65]/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src={selectedFace.previewUrl}
              alt={selectedFace.name}
              className="w-12 h-12 rounded-xl object-cover border border-[#D6AD65]"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white">{selectedFace.name}</span>
                <Badge variant={selectedFace.isDemo ? 'demo' : 'emerald'}>
                  {selectedFace.isDemo ? 'Demo Preset' : 'Custom Upload'}
                </Badge>
              </div>
              <p className="text-xs text-[#A1A1AA]">
                Landmarks: 468 points mapped • Quality: {selectedFace.qualityRating}
              </p>
            </div>
          </div>
          <span className="text-xs text-[#D6AD65] font-semibold hidden sm:inline-flex items-center gap-1">
            <Check className="w-4 h-4" /> Ready for Alignment
          </span>
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
                className={`px-3 py-1 text-xs rounded-lg border transition-all cursor-pointer ${
                  categoryFilter === cat
                    ? 'bg-[#2A2418] border-[#D6AD65] text-[#F4DE9C]'
                    : 'bg-[#14141B] border-[#252532] text-[#8E8E9E] hover:border-[#38384A]'
                }`}
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
                  className={`relative bg-[#16161D] border rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 group hover:-translate-y-1 ${
                    isSelected
                      ? 'border-[#D6AD65] shadow-[0_0_20px_rgba(214,173,101,0.2)] bg-[#1B1A22]'
                      : 'border-[#272736] hover:border-[#3D3D52]'
                  }`}
                >
                  {/* Actor image */}
                  <div className="relative aspect-[4/3] overflow-hidden bg-black">
                    <img
                      src={preset.avatarUrl}
                      alt={preset.name}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#16161D] via-transparent to-black/30" />

                    {/* Demo badge overlay */}
                    <div className="absolute top-3 left-3">
                      <Badge variant="demo">Demo Preset</Badge>
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
                      <h4 className="text-base font-cinematic font-bold text-white group-hover:text-[#D6AD65] transition-colors">
                        {preset.name}
                      </h4>
                      <p className="text-xs text-[#D6AD65] font-medium">{preset.title}</p>
                    </div>

                    <p className="text-xs text-[#8E8E9E] line-clamp-2 mb-3">
                      {preset.description}
                    </p>

                    <div className="pt-2.5 border-t border-[#252533] flex items-center justify-between text-[11px] text-[#A1A1AA]">
                      <span className="font-mono text-[#71717A]">{preset.era}</span>
                      <span className="text-[#D6AD65] group-hover:underline">Select Actor →</span>
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
            className="border-2 border-dashed border-[#2C2C3A] hover:border-[#D6AD65]/60 rounded-2xl p-8 sm:p-12 text-center transition-all cursor-pointer bg-[#141419]/80 hover:bg-[#181822] group"
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

            <div className="w-16 h-16 rounded-2xl bg-[#20202B] border border-[#2F2F3F] flex items-center justify-center text-[#D6AD65] mx-auto mb-4 group-hover:scale-110 group-hover:border-[#D6AD65]/50 transition-all shadow-lg">
              <Upload className="w-7 h-7" />
            </div>

            <h3 className="text-base font-semibold text-white mb-1">
              Upload Front-Facing Actor Portrait
            </h3>
            <p className="text-xs text-[#8E8E9E] max-w-md mx-auto mb-4">
              Upload JPG or PNG up to 10MB. For optimal re-targeting, use a high-resolution, evenly-lit headshot looking directly into the lens.
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
                <div className="w-full bg-[#20202B] h-2 rounded-full overflow-hidden">
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

          {/* Honest guidelines note */}
          <div className="p-3.5 rounded-xl bg-[#171720] border border-[#262635] flex items-start gap-2.5 text-xs text-[#8E8E9E]">
            <Info className="w-4 h-4 text-[#D6AD65] shrink-0 mt-0.5" />
            <p>
              <strong className="text-white">Studio Quality Guidelines:</strong> Avoid heavy sunglasses, extreme head tilts, or motion blur. The neural model normalizes ambient light to match the destination frame.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

