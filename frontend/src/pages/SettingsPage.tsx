import React, { useState } from 'react';
import {
  User,
  Sliders,
  Server,
  RotateCcw,
  Check,
  Activity,
  Save,
  Key,
} from 'lucide-react';
import { useSettings } from '../context/SettingsContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';

export const SettingsPage: React.FC = () => {
  const {
    settings,
    updateProfile,
    updatePreferences,
    updateApiConfig,
    testBackendConnection,
    resetToDefaultDemoData,
  } = useSettings();

  const [activeTab, setActiveTab] = useState<'profile' | 'preferences' | 'api'>('profile');
  const [profileForm, setProfileForm] = useState(settings.profile);
  const [prefsForm, setPrefsForm] = useState(settings.preferences);
  const [apiForm, setApiForm] = useState(settings.apiConfig);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isTestingApi, setIsTestingApi] = useState(false);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfile(profileForm);
    triggerSuccessBanner();
  };

  const handleSavePreferences = (e: React.FormEvent) => {
    e.preventDefault();
    updatePreferences(prefsForm);
    triggerSuccessBanner();
  };

  const handleSaveApi = (e: React.FormEvent) => {
    e.preventDefault();
    updateApiConfig(apiForm);
    triggerSuccessBanner();
  };

  const triggerSuccessBanner = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleTestConnection = async () => {
    setIsTestingApi(true);
    await testBackendConnection();
    setIsTestingApi(false);
  };

  return (
    <div className="space-y-6 pb-12 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-cinematic font-bold text-white flex items-center gap-2.5">
          <Sliders className="w-6 h-6 text-[#D6AD65]" />
          Studio Settings & AI Parameters
        </h1>
        <p className="text-xs sm:text-sm text-[#8E8E9E]">
          Configure directorial profile, neural default parameters, and future FastAPI endpoints
        </p>
      </div>

      {/* Success Notification */}
      {saveSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/40 flex items-center gap-2.5 text-xs text-emerald-300">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>Settings successfully updated in local studio storage.</span>
        </div>
      )}

      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-[#242432] space-x-6 text-sm">
        <button
          onClick={() => setActiveTab('profile')}
          className={`pb-3 font-medium transition-colors cursor-pointer flex items-center gap-2 ${
            activeTab === 'profile'
              ? 'text-[#D6AD65] border-b-2 border-[#D6AD65]'
              : 'text-[#8E8E9E] hover:text-white'
          }`}
        >
          <User className="w-4 h-4" />
          Directorial Profile
        </button>

        <button
          onClick={() => setActiveTab('preferences')}
          className={`pb-3 font-medium transition-colors cursor-pointer flex items-center gap-2 ${
            activeTab === 'preferences'
              ? 'text-[#D6AD65] border-b-2 border-[#D6AD65]'
              : 'text-[#8E8E9E] hover:text-white'
          }`}
        >
          <Sliders className="w-4 h-4" />
          AI & Pipeline Defaults
        </button>

        <button
          onClick={() => setActiveTab('api')}
          className={`pb-3 font-medium transition-colors cursor-pointer flex items-center gap-2 ${
            activeTab === 'api'
              ? 'text-[#D6AD65] border-b-2 border-[#D6AD65]'
              : 'text-[#8E8E9E] hover:text-white'
          }`}
        >
          <Server className="w-4 h-4" />
          FastAPI Backend Link
        </button>
      </div>

      {/* Tab 1: Profile */}
      {activeTab === 'profile' && (
        <Card className="p-6">
          <form onSubmit={handleSaveProfile} className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center gap-5 pb-6 border-b border-[#242432]">
              <img
                src={profileForm.avatarUrl}
                alt={profileForm.name}
                className="w-20 h-20 rounded-2xl object-cover border-2 border-[#D6AD65]"
              />
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-white">{profileForm.name}</h3>
                <p className="text-xs text-[#D6AD65]">{profileForm.role}</p>
                <p className="text-xs text-[#71717A] font-mono">
                  Member of {profileForm.studioName}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Full Director Name</label>
                <input
                  type="text"
                  value={profileForm.name}
                  onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Production Email</label>
                <input
                  type="email"
                  value={profileForm.email}
                  onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Production House / Studio</label>
                <input
                  type="text"
                  value={profileForm.studioName}
                  onChange={(e) => setProfileForm({ ...profileForm, studioName: e.target.value })}
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Role / Designation</label>
                <input
                  type="text"
                  value={profileForm.role}
                  onChange={(e) => setProfileForm({ ...profileForm, role: e.target.value })}
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-[#242432] flex justify-end">
              <Button type="submit" size="sm" variant="primary" leftIcon={<Save className="w-3.5 h-3.5" />}>
                Save Profile Changes
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Tab 2: Preferences */}
      {activeTab === 'preferences' && (
        <Card className="p-6">
          <form onSubmit={handleSavePreferences} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Default Export Quality</label>
                <select
                  value={prefsForm.defaultResolution}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, defaultResolution: e.target.value as any })
                  }
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                >
                  <option value="720p">720p HD Ready</option>
                  <option value="1080p">1080p Full HD Cinematic</option>
                  <option value="4k">4K Ultra Cinema Master</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Default Color Grading Profile</label>
                <select
                  value={prefsForm.colorGradingDefault}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, colorGradingDefault: e.target.value as any })
                  }
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                >
                  <option value="authentic">Authentic Raw Camera Tone</option>
                  <option value="warm-vintage">90s Golden Nostalgia</option>
                  <option value="vibrant-masala">Vibrant Masala Extravaganza</option>
                  <option value="moody-noir">Moody Neo-Noir Crime</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Watermark Placement</label>
                <select
                  value={prefsForm.watermarkPlacement}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, watermarkPlacement: e.target.value as any })
                  }
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                >
                  <option value="bottom-right">Bottom-Right Corner</option>
                  <option value="bottom-left">Bottom-Left Corner</option>
                  <option value="none">No Visible Watermark (C2PA metadata only)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-[#A1A1AA] font-mono">Cloud Retention Window</label>
                <select
                  value={prefsForm.retentionDays}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, retentionDays: Number(e.target.value) })
                  }
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-[#D6AD65]"
                >
                  <option value={7}>7 Days Cache</option>
                  <option value={30}>30 Days Studio Archive</option>
                  <option value={90}>90 Days Enterprise Vault</option>
                </select>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <label className="flex items-center gap-2.5 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={prefsForm.autoFaceEnhance}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, autoFaceEnhance: e.target.checked })
                  }
                  className="rounded text-[#D6AD65] bg-[#09090B] border-[#38384A]"
                />
                <span className="text-[#EDEDED]">
                  Enable Neural Super-Resolution & Skin Texture Restoration by default
                </span>
              </label>

              <label className="flex items-center gap-2.5 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={prefsForm.audioPassthrough}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, audioPassthrough: e.target.checked })
                  }
                  className="rounded text-[#D6AD65] bg-[#09090B] border-[#38384A]"
                />
                <span className="text-[#EDEDED]">
                  Preserve Original Audio Stream & Stereo Mixing
                </span>
              </label>
            </div>

            <div className="pt-4 border-t border-[#242432] flex justify-end">
              <Button type="submit" size="sm" variant="primary" leftIcon={<Save className="w-3.5 h-3.5" />}>
                Save Preferences
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Tab 3: API Backend Config */}
      {activeTab === 'api' && (
        <Card className="p-6 space-y-6">
          <div className="flex items-start justify-between gap-4 pb-4 border-b border-[#242432]">
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Server className="w-4 h-4 text-[#D6AD65]" />
                FastAPI Integration Bridge
              </h3>
              <p className="text-xs text-[#8E8E9E] mt-0.5">
                The frontend is pre-architected with typed API contracts ready to connect to a FastAPI backend.
              </p>
            </div>

            <Badge
              variant={
                settings.apiConfig.useLiveBackend
                  ? 'emerald'
                  : settings.apiConfig.connectionStatus === 'connected'
                  ? 'gold'
                  : 'demo'
              }
            >
              {settings.apiConfig.useLiveBackend ? 'Live Backend Active' : 'Frontend Demo Mode'}
            </Badge>
          </div>

          <form onSubmit={handleSaveApi} className="space-y-4">
            <div className="space-y-1.5 text-xs">
              <label className="text-[#A1A1AA] font-mono">FastAPI Base Endpoint URL</label>
              <input
                type="text"
                value={apiForm.backendUrl}
                onChange={(e) => setApiForm({ ...apiForm, backendUrl: e.target.value })}
                placeholder="http://127.0.0.1:8000/api/v1"
                className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl px-3.5 py-2 text-white font-mono text-xs focus:outline-none focus:border-[#D6AD65]"
              />
            </div>

            <div className="space-y-1.5 text-xs">
              <label className="text-[#A1A1AA] font-mono">Studio Bearer Token / API Key</label>
              <div className="relative">
                <input
                  type="password"
                  value={apiForm.apiKey}
                  onChange={(e) => setApiForm({ ...apiForm, apiKey: e.target.value })}
                  placeholder="bolly_live_sec_..."
                  className="w-full bg-[#14141B] border border-[#2B2B3C] rounded-xl pl-9 pr-3.5 py-2 text-white font-mono text-xs focus:outline-none focus:border-[#D6AD65]"
                />
                <Key className="w-4 h-4 text-[#71717A] absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2.5 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={apiForm.useLiveBackend}
                  onChange={(e) => setApiForm({ ...apiForm, useLiveBackend: e.target.checked })}
                  className="rounded text-[#D6AD65] bg-[#09090B] border-[#38384A]"
                />
                <span className="text-white font-medium">
                  Route requests to Live FastAPI Backend (Disable local simulation fallback)
                </span>
              </label>
            </div>

            <div className="pt-4 border-t border-[#242432] flex items-center justify-between">
              <Button
                type="button"
                size="sm"
                variant="outline"
                isLoading={isTestingApi}
                onClick={handleTestConnection}
                leftIcon={<Activity className="w-3.5 h-3.5" />}
              >
                Test Endpoint Ping
              </Button>

              <Button type="submit" size="sm" variant="primary" leftIcon={<Save className="w-3.5 h-3.5" />}>
                Save API Config
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Danger Zone: Reset Demo Data */}
      <Card className="p-6 border-red-900/30 bg-[#161214]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-red-300 flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-red-400" />
              Reset Local Storage & Demo Data
            </h3>
            <p className="text-xs text-[#8E8E9E] mt-0.5">
              Restores initial Bollywood demo projects, sample footage, and default quotas.
            </p>
          </div>

          <Button
            size="sm"
            variant="danger"
            onClick={() => {
              if (window.confirm('Reset all demo projects and return to initial factory state?')) {
                resetToDefaultDemoData();
              }
            }}
          >
            Reset All Demo Data
          </Button>
        </div>
      </Card>
    </div>
  );
};
