import React, { useState } from 'react';
import { ShieldAlert, Lock, Sparkles } from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';

interface ConsentGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmConsent: () => void;
}

export const ConsentGateModal: React.FC<ConsentGateModalProps> = ({
  isOpen,
  onClose,
  onConfirmConsent,
}) => {
  const [agreedRights, setAgreedRights] = useState(false);
  const [agreedEthical, setAgreedEthical] = useState(false);
  const [agreedWatermark, setAgreedWatermark] = useState(true);

  const canProceed = agreedRights && agreedEthical && agreedWatermark;

  const handleAuthorize = () => {
    if (!canProceed) return;
    onConfirmConsent();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="lg"
      title={
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-[#D6AD65]" />
          <span>Likeness Consent & Terms</span>
        </div>
      }
      description="Please confirm consent prior to processing the video"
    >
      <div className="space-y-5 text-sm">
        {/* Notice box */}
        <div
          className="p-4 rounded-xl border text-xs leading-relaxed"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
            color: 'var(--text-secondary)',
          }}
        >
          <p className="font-semibold mb-1 flex items-center gap-1.5" style={{ color: 'var(--gold)' }}>
            <Lock className="w-3.5 h-3.5" />
            Usage & Ethical Guidelines
          </p>
          You agree to only use face swapping for lawful, authorized creative purposes. Generating non-consensual imagery, deceptive impersonation, or defamatory content is strictly prohibited.
        </div>

        {/* Checkboxes */}
        <div className="space-y-3.5">
          {/* Check 1 */}
          <label
            className="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors"
            style={{
              backgroundColor: 'var(--bg-input)',
              borderColor: 'var(--border)',
            }}
          >
            <input
              type="checkbox"
              checked={agreedRights}
              onChange={(e) => setAgreedRights(e.target.checked)}
              className="mt-1 w-4 h-4 rounded text-[#D6AD65] cursor-pointer"
            />
            <div className="text-xs">
              <span className="font-semibold block" style={{ color: 'var(--text-primary)' }}>
                Likeness Rights & Authorization
              </span>
              <span style={{ color: 'var(--text-faint)' }}>
                I affirm that I have permission or lawful likeness consent to use these images and video materials.
              </span>
            </div>
          </label>

          {/* Check 2 */}
          <label
            className="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors"
            style={{
              backgroundColor: 'var(--bg-input)',
              borderColor: 'var(--border)',
            }}
          >
            <input
              type="checkbox"
              checked={agreedEthical}
              onChange={(e) => setAgreedEthical(e.target.checked)}
              className="mt-1 w-4 h-4 rounded text-[#D6AD65] cursor-pointer"
            />
            <div className="text-xs">
              <span className="font-semibold block" style={{ color: 'var(--text-primary)' }}>
                Ethical Creative Purpose
              </span>
              <span style={{ color: 'var(--text-faint)' }}>
                This output will not be used for deceptive impersonation, harassment, or unlawful distribution.
              </span>
            </div>
          </label>

          {/* Check 3 */}
          <label
            className="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors"
            style={{
              backgroundColor: 'var(--bg-input)',
              borderColor: 'var(--border)',
            }}
          >
            <input
              type="checkbox"
              checked={agreedWatermark}
              onChange={(e) => setAgreedWatermark(e.target.checked)}
              className="mt-1 w-4 h-4 rounded text-[#D6AD65] cursor-pointer"
            />
            <div className="text-xs">
              <span className="font-semibold block" style={{ color: 'var(--text-primary)' }}>
                Terms of Service
              </span>
              <span style={{ color: 'var(--text-faint)' }}>
                I understand and agree to the platform's terms of service and content policies.
              </span>
            </div>
          </label>
        </div>

        {/* Action Button */}
        <div className="pt-3 border-t flex items-center justify-end gap-3" style={{ borderColor: 'var(--border)' }}>
          <Button size="sm" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="md"
            variant="primary"
            disabled={!canProceed}
            leftIcon={<Sparkles className="w-4 h-4" />}
            onClick={handleAuthorize}
          >
            Confirm & Start Processing
          </Button>
        </div>
      </div>
    </Modal>
  );
};
