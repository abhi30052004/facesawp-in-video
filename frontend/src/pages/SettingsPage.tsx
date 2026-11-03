import React, { useState } from 'react';
import {
  Sliders,
  Save,
  Waves,
  Shield,
  Film,
  CheckCircle2,
} from 'lucide-react';
import { useSettings } from '../context/SettingsContext';
import { Button } from '../components/common/Button';

/* ─── small helpers ──────────────────────────────────────────── */

const inputCls =
  'w-full rounded-xl px-3.5 py-2.5 text-sm focus:outline-none transition-colors border';
const inputStyle = {
  backgroundColor: 'var(--bg-input)',
  borderColor: 'var(--border)',
  color: 'var(--text-primary)',
};

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
      {children}
    </span>
  );
}

function SectionCard({
  icon: Icon,
  title,
  subtitle,
  children,
  accent = '#D6AD65',
}: {
  icon: React.ElementType;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  accent?: string;
}) {
  return (
    <div
      className="rounded-2xl border overflow-hidden"
      style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}
    >
      {/* Card header */}
      <div
        className="flex items-center gap-3 px-5 py-4 border-b"
        style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-input)' }}
      >
        <div
          className="p-2 rounded-lg shrink-0"
          style={{ background: `${accent}18`, color: accent }}
        >
          <Icon className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            {title}
          </h3>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            {subtitle}
          </p>
        </div>
      </div>
      {/* Card body */}
      <div className="p-5">{children}</div>
    </div>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b last:border-0" style={{ borderColor: 'var(--border)' }}>
      <div>
        <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{label}</p>
        {description && (
          <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{description}</p>
        )}
      </div>
      {/* Toggle switch */}
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className="relative w-10 h-5.5 rounded-full transition-colors shrink-0 focus:outline-none"
        style={{
          background: checked ? '#D6AD65' : 'var(--bg-input)',
          border: `1px solid ${checked ? '#D6AD65' : 'var(--border)'}`,
          width: 40,
          height: 22,
        }}
        aria-checked={checked}
        role="switch"
      >
        <span
          className="absolute top-0.5 rounded-full bg-white shadow-sm transition-all"
          style={{
            width: 17,
            height: 17,
            left: checked ? 20 : 2,
            top: 2,
          }}
        />
      </button>
    </div>
  );
}

/* ─── main page ──────────────────────────────────────────────── */

export const SettingsPage: React.FC = () => {
  const {
    settings,
    updatePreferences,
  } = useSettings();

  const [prefsForm, setPrefsForm] = useState(settings.preferences);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const flash = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleSavePreferences = (e: React.FormEvent) => {
    e.preventDefault();
    updatePreferences(prefsForm);
    flash();
  };

  return (
    <div className="space-y-8 pb-16 max-w-3xl mx-auto">

      {/* ── Page Title ── */}
      <div>
        <h1
          className="text-2xl sm:text-3xl font-cinematic font-bold flex items-center gap-2.5"
          style={{ color: 'var(--text-primary)' }}
        >
          <Sliders className="w-6 h-6 text-[#D6AD65]" />
          Settings
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Configure your processing preferences.
        </p>
      </div>

      {/* ── Success toast ── */}
      {saveSuccess && (
        <div className="flex items-center gap-2.5 p-3.5 rounded-xl text-sm text-emerald-400 border bg-emerald-950/30 border-emerald-500/30">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          Settings saved successfully.
        </div>
      )}

      {/* ── Preferences ── */}
      <SectionCard
        icon={Sliders}
        title="Processing Preferences"
        subtitle="Default output quality and pipeline behaviour"
      >
        <form onSubmit={handleSavePreferences} className="space-y-5">

          {/* Two select dropdowns */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label>Export Resolution</Label>
              <select
                value={prefsForm.defaultResolution}
                onChange={e => setPrefsForm({ ...prefsForm, defaultResolution: e.target.value as any })}
                className={inputCls}
                style={inputStyle}
              >
                <option value="720p">720p — HD</option>
                <option value="1080p">1080p — Full HD</option>
                <option value="4k">4K — Ultra HD</option>
              </select>
            </div>

            <div>
              <Label>Compliance Watermark</Label>
              <select
                value={prefsForm.watermarkPlacement}
                onChange={e => setPrefsForm({ ...prefsForm, watermarkPlacement: e.target.value as any })}
                className={inputCls}
                style={inputStyle}
              >
                <option value="bottom-right">Bottom-Right</option>
                <option value="bottom-left">Bottom-Left</option>
                <option value="none">Disabled</option>
              </select>
            </div>
          </div>

          {/* Toggles */}
          <div
            className="rounded-xl border overflow-hidden"
            style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-input)' }}
          >
            <ToggleRow
              label="Auto Face Enhancement"
              description="Sharpens and colour-corrects each swapped frame automatically."
              checked={prefsForm.autoFaceEnhance}
              onChange={v => setPrefsForm({ ...prefsForm, autoFaceEnhance: v })}
            />
            <ToggleRow
              label="Preserve Original Audio"
              description="Re-mux original AAC stereo audio into the output MP4."
              checked={prefsForm.audioPassthrough}
              onChange={v => setPrefsForm({ ...prefsForm, audioPassthrough: v })}
            />
            <ToggleRow
              label="Notify on Job Complete"
              description="Browser notification when face swap finishes."
              checked={prefsForm.sendNotificationOnComplete}
              onChange={v => setPrefsForm({ ...prefsForm, sendNotificationOnComplete: v })}
            />
          </div>

          <div className="flex justify-end pt-1">
            <Button type="submit" size="sm" variant="primary" leftIcon={<Save className="w-3.5 h-3.5" />}>
              Save Preferences
            </Button>
          </div>
        </form>
      </SectionCard>

      {/* ── Info row ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { icon: Shield,  label: 'Local Only',     desc: 'No biometric data leaves your device.' },
          { icon: Film,    label: 'Ghost-256 CPU',  desc: 'Apache-2.0 licensed ONNX model.' },
          { icon: Waves,   label: 'Audio Preserved', desc: 'AAC 48 kHz stereo re-mux.' },
        ].map(item => (
          <div
            key={item.label}
            className="flex items-start gap-3 p-4 rounded-xl border"
            style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}
          >
            <item.icon className="w-4 h-4 mt-0.5 shrink-0 text-[#D6AD65]" />
            <div>
              <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{item.label}</p>
              <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{item.desc}</p>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};
