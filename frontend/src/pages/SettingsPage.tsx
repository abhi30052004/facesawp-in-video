import React, { useState } from 'react';
import {
  User,
  Sliders,
  Check,
  Save,
} from 'lucide-react';
import { useSettings } from '../context/SettingsContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';

export const SettingsPage: React.FC = () => {
  const {
    settings,
    updateProfile,
    updatePreferences,
  } = useSettings();

  const [activeTab, setActiveTab] = useState<'profile' | 'preferences'>('profile');
  const [profileForm, setProfileForm] = useState(settings.profile);
  const [prefsForm, setPrefsForm] = useState(settings.preferences);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const triggerSuccessBanner = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

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

  return (
    <div className="space-y-6 pb-12 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1
          className="text-2xl sm:text-3xl font-cinematic font-bold flex items-center gap-2.5"
          style={{ color: 'var(--text-primary)' }}
        >
          <Sliders className="w-6 h-6 text-[#D6AD65]" />
          Settings
        </h1>
        <p className="text-xs sm:text-sm" style={{ color: 'var(--text-faint)' }}>
          Manage your profile and processing preferences
        </p>
      </div>

      {/* Success Notification */}
      {saveSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/40 flex items-center gap-2.5 text-xs text-emerald-400">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>Settings saved successfully.</span>
        </div>
      )}

      {/* Settings Navigation Tabs */}
      <div className="flex border-b space-x-6 text-sm" style={{ borderColor: 'var(--border)' }}>
        <button
          onClick={() => setActiveTab('profile')}
          className="pb-3 font-medium transition-colors cursor-pointer flex items-center gap-2"
          style={{
            color: activeTab === 'profile' ? 'var(--gold)' : 'var(--text-muted)',
            borderBottom: activeTab === 'profile' ? '2px solid var(--gold)' : '2px solid transparent',
          }}
        >
          <User className="w-4 h-4" />
          Profile
        </button>

        <button
          onClick={() => setActiveTab('preferences')}
          className="pb-3 font-medium transition-colors cursor-pointer flex items-center gap-2"
          style={{
            color: activeTab === 'preferences' ? 'var(--gold)' : 'var(--text-muted)',
            borderBottom: activeTab === 'preferences' ? '2px solid var(--gold)' : '2px solid transparent',
          }}
        >
          <Sliders className="w-4 h-4" />
          Preferences
        </button>
      </div>

      {/* Tab 1: Profile */}
      {activeTab === 'profile' && (
        <Card className="p-6">
          <form onSubmit={handleSaveProfile} className="space-y-6">
            <div
              className="flex flex-col sm:flex-row sm:items-center gap-5 pb-6 border-b"
              style={{ borderColor: 'var(--border)' }}
            >
              <img
                src={profileForm.avatarUrl}
                alt={profileForm.name}
                className="w-20 h-20 rounded-2xl object-cover border-2"
                style={{ borderColor: 'var(--gold)' }}
              />
              <div className="space-y-1">
                <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {profileForm.name}
                </h3>
                <p className="text-xs" style={{ color: 'var(--gold)' }}>
                  {profileForm.role}
                </p>
                <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                  {profileForm.studioName}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1.5">
                <label className="font-mono block" style={{ color: 'var(--text-secondary)' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  value={profileForm.name}
                  onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                  className="w-full rounded-xl px-3.5 py-2 text-xs focus:outline-none transition-colors border"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-mono block" style={{ color: 'var(--text-secondary)' }}>
                  Email
                </label>
                <input
                  type="email"
                  value={profileForm.email}
                  onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                  className="w-full rounded-xl px-3.5 py-2 text-xs focus:outline-none transition-colors border"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-mono block" style={{ color: 'var(--text-secondary)' }}>
                  Organization
                </label>
                <input
                  type="text"
                  value={profileForm.studioName}
                  onChange={(e) => setProfileForm({ ...profileForm, studioName: e.target.value })}
                  className="w-full rounded-xl px-3.5 py-2 text-xs focus:outline-none transition-colors border"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-mono block" style={{ color: 'var(--text-secondary)' }}>
                  Role
                </label>
                <input
                  type="text"
                  value={profileForm.role}
                  onChange={(e) => setProfileForm({ ...profileForm, role: e.target.value })}
                  className="w-full rounded-xl px-3.5 py-2 text-xs focus:outline-none transition-colors border"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>
            </div>

            <div className="pt-4 border-t flex justify-end" style={{ borderColor: 'var(--border)' }}>
              <Button type="submit" size="sm" variant="primary" leftIcon={<Save className="w-3.5 h-3.5" />}>
                Save Profile
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
                <label className="font-mono block" style={{ color: 'var(--text-secondary)' }}>
                  Default Export Quality
                </label>
                <select
                  value={prefsForm.defaultResolution}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, defaultResolution: e.target.value as any })
                  }
                  className="w-full rounded-xl px-3.5 py-2 text-xs focus:outline-none transition-colors border"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <option value="720p">720p</option>
                  <option value="1080p">1080p Full HD</option>
                  <option value="4k">4K</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="font-mono block" style={{ color: 'var(--text-secondary)' }}>
                  Watermark
                </label>
                <select
                  value={prefsForm.watermarkPlacement}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, watermarkPlacement: e.target.value as any })
                  }
                  className="w-full rounded-xl px-3.5 py-2 text-xs focus:outline-none transition-colors border"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <option value="bottom-right">Bottom-Right</option>
                  <option value="bottom-left">Bottom-Left</option>
                  <option value="none">No Watermark</option>
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
                  className="rounded text-[#D6AD65]"
                />
                <span style={{ color: 'var(--text-primary)' }}>Enable face enhancement by default</span>
              </label>

              <label className="flex items-center gap-2.5 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={prefsForm.audioPassthrough}
                  onChange={(e) =>
                    setPrefsForm({ ...prefsForm, audioPassthrough: e.target.checked })
                  }
                  className="rounded text-[#D6AD65]"
                />
                <span style={{ color: 'var(--text-primary)' }}>Preserve original audio in output video</span>
              </label>
            </div>

            <div className="pt-4 border-t flex justify-end" style={{ borderColor: 'var(--border)' }}>
              <Button type="submit" size="sm" variant="primary" leftIcon={<Save className="w-3.5 h-3.5" />}>
                Save Preferences
              </Button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
};
