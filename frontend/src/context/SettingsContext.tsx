import React, { createContext, useContext, useEffect, useState } from 'react';
import { ApiConnectionConfig, StudioAiPreferences, StudioSettings, UserProfile } from '../types/settings';
import { INITIAL_STUDIO_SETTINGS } from '../services/mockData';
import { bollySwapApi } from '../services/api';

const SETTINGS_STORAGE_KEY = 'bollyswap_studio_settings_v1';

interface SettingsContextType {
  settings: StudioSettings;
  updateProfile: (profile: Partial<UserProfile>) => void;
  updatePreferences: (prefs: Partial<StudioAiPreferences>) => void;
  updateApiConfig: (config: Partial<ApiConnectionConfig>) => void;
  testBackendConnection: () => Promise<boolean>;
  resetToDefaultDemoData: () => void;
}

const SettingsContext = createContext<SettingsContextType | null>(null);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<StudioSettings>(() => {
    try {
      const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Use defaults
    }
    return INITIAL_STUDIO_SETTINGS;
  });

  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
      bollySwapApi.configure(
        settings.apiConfig.backendUrl,
        settings.apiConfig.apiKey,
        settings.apiConfig.useLiveBackend
      );
    } catch (e) {
      console.warn('Failed to persist settings', e);
    }
  }, [settings]);

  const updateProfile = (profileUpdate: Partial<UserProfile>) => {
    setSettings((prev) => ({
      ...prev,
      profile: { ...prev.profile, ...profileUpdate },
    }));
  };

  const updatePreferences = (prefsUpdate: Partial<StudioAiPreferences>) => {
    setSettings((prev) => ({
      ...prev,
      preferences: { ...prev.preferences, ...prefsUpdate },
    }));
  };

  const updateApiConfig = (configUpdate: Partial<ApiConnectionConfig>) => {
    setSettings((prev) => ({
      ...prev,
      apiConfig: { ...prev.apiConfig, ...configUpdate },
    }));
  };

  const testBackendConnection = async (): Promise<boolean> => {
    updateApiConfig({ connectionStatus: 'testing' });
    const start = performance.now();
    try {
      const health = await bollySwapApi.checkBackendHealth(settings.apiConfig.backendUrl);
      const ping = Math.round(performance.now() - start);

      if (health.status === 'online') {
        updateApiConfig({ connectionStatus: 'connected', lastPingMs: ping });
        return true;
      } else {
        updateApiConfig({ connectionStatus: 'offline_demo', lastPingMs: ping });
        return false;
      }
    } catch {
      updateApiConfig({ connectionStatus: 'disconnected' });
      return false;
    }
  };

  const resetToDefaultDemoData = () => {
    localStorage.clear();
    setSettings(INITIAL_STUDIO_SETTINGS);
    window.location.reload();
  };

  return (
    <SettingsContext.Provider
      value={{
        settings,
        updateProfile,
        updatePreferences,
        updateApiConfig,
        testBackendConnection,
        resetToDefaultDemoData,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};

