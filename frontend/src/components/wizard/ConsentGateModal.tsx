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
          <span>Ethical AI & Likeness Consent Gate</span>
        </div>
      }
      description="Mandatory compliance check prior to neural video processing"
    >
      <div className="space-y-5 text-sm">
        {/* Notice box */}
        <div className="p-4 rounded-xl bg-gradient-to-r from-[#8E3048]/20 via-[#1C1820] to-[#D6AD65]/10 border border-[#8E3048]/40 text-[#EDEDED] leading-relaxed text-xs">
          <p className="font-semibold text-[#FFA8BD] mb-1 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            Studio Governance Policy (Responsible Creative AI)
          </p>
          BollySwap AI operates under strict ethical guidelines. Deepfake and synthetic media generation without legal permission, impersonation for fraud, defaming individuals, or creating non-consensual imagery is strictly prohibited and subject to account suspension and legal action.
        </div>

        {/* Checkboxes */}
        <div className="space-y-3.5">
          {/* Check 1 */}
          <label className="flex items-start gap-3 p-3 rounded-xl bg-[#14141B] border border-[#252532] hover:border-[#38384A] cursor-pointer transition-colors">
            <input
              type="checkbox"
              checked={agreedRights}
              onChange={(e) => setAgreedRights(e.target.checked)}
              className="mt-1 w-4 h-4 rounded text-[#D6AD65] bg-[#09090B] border-[#38384A] focus:ring-[#D6AD65] cursor-pointer"
            />
            <div className="text-xs">
              <span className="font-semibold text-white block">
                Likeness Rights & Authorization
              </span>
              <span className="text-[#8E8E9E]">
                I affirm that I own the rights, have obtained lawful likeness consent, or am utilizing authorized demo/fair-use materials for creative filmmaking.
              </span>
            </div>
          </label>

          {/* Check 2 */}
          <label className="flex items-start gap-3 p-3 rounded-xl bg-[#14141B] border border-[#252532] hover:border-[#38384A] cursor-pointer transition-colors">
            <input
              type="checkbox"
              checked={agreedEthical}
              onChange={(e) => setAgreedEthical(e.target.checked)}
              className="mt-1 w-4 h-4 rounded text-[#D6AD65] bg-[#09090B] border-[#38384A] focus:ring-[#D6AD65] cursor-pointer"
            />
            <div className="text-xs">
              <span className="font-semibold text-white block">
                Ethical Creative Purpose
              </span>
              <span className="text-[#8E8E9E]">
                This synthesis will not be used for deceptive impersonation, political manipulation, harassment, or defamatory distribution.
              </span>
            </div>
          </label>

          {/* Check 3 */}
          <label className="flex items-start gap-3 p-3 rounded-xl bg-[#14141B] border border-[#252532] hover:border-[#38384A] cursor-pointer transition-colors">
            <input
              type="checkbox"
              checked={agreedWatermark}
              onChange={(e) => setAgreedWatermark(e.target.checked)}
              className="mt-1 w-4 h-4 rounded text-[#D6AD65] bg-[#09090B] border-[#38384A] focus:ring-[#D6AD65] cursor-pointer"
            />
            <div className="text-xs">
              <span className="font-semibold text-white block">
                Digital Provenance & Watermark Acknowledgment
              </span>
              <span className="text-[#8E8E9E]">
                I acknowledge that the exported preview incorporates BollySwap synthetic media metadata and preview provenance watermarking.
              </span>
            </div>
          </label>
        </div>

        {/* Buttons */}
        <div className="pt-3 border-t border-[#22222E] flex items-center justify-end gap-3">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            disabled={!canProceed}
            onClick={handleAuthorize}
            leftIcon={<Sparkles className="w-4 h-4" />}
          >
            Authorize & Launch Pipeline
          </Button>
        </div>
      </div>
    </Modal>
  );
};
