import React, { useRef, useState } from 'react';
import {
  Play,
  Pause,
  Download,
  Trash2,
  ShieldCheck,
  Film,
} from 'lucide-react';
import { FaceSwapProject } from '../../types/project';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { formatDate } from '../../utils/formatters';

interface ProjectDetailModalProps {
  project: FaceSwapProject | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete: (id: string) => void;
}

export const ProjectDetailModal: React.FC<ProjectDetailModalProps> = ({
  project,
  isOpen,
  onClose,
  onDelete,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  if (!project) return null;

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const videoUrl =
    project.result?.outputVideoUrl ||
    project.sourceVideo?.url ||
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4';

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = `${project.title.replace(/\s+/g, '_')}_Master.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="4xl"
      title={
        <div className="flex items-center gap-2">
          <Film className="w-5 h-5 text-[#D6AD65]" />
          <span>{project.title}</span>
        </div>
      }
      description={`Master render created on ${formatDate(project.createdAt)}`}
    >
      <div className="space-y-6">
        {/* Main Video Stage */}
        <div className="relative aspect-video max-h-[460px] bg-black rounded-2xl overflow-hidden border border-[#2B2B3B] group">
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full h-full object-contain"
            onEnded={() => setIsPlaying(false)}
          />

          {/* Big Play Button Overlay */}
          <button
            onClick={togglePlay}
            aria-label={isPlaying ? 'Pause video' : 'Play video'}
            className="absolute inset-0 m-auto w-14 h-14 rounded-full bg-black/60 backdrop-blur-md border border-[#D6AD65]/40 text-[#D6AD65] flex items-center justify-center hover:scale-110 transition-all cursor-pointer shadow-xl"
          >
            {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-0.5" />}
          </button>

          {/* Badges on video */}
          <div className="absolute top-3 left-3 flex items-center gap-2">
            <Badge variant="emerald">Master Output</Badge>
            <Badge variant="demo">Demo Simulation</Badge>
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Target Actor Identity */}
          <div className="p-4 rounded-xl bg-[#14141B] border border-[#252533] flex items-center gap-3">
            <img
              src={
                project.targetFace?.previewUrl ||
                'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80'
              }
              alt={project.targetFace?.name}
              className="w-12 h-12 rounded-xl object-cover border border-[#D6AD65]"
            />
            <div>
              <span className="text-[10px] font-mono uppercase text-[#71717A] block">
                Target Actor
              </span>
              <span className="text-sm font-semibold text-white">
                {project.targetFace?.name || 'Actor Persona'}
              </span>
              <span className="text-xs text-[#D6AD65] block">
                {project.targetFace?.isDemo ? 'Preset Archetype' : 'Custom Upload'}
              </span>
            </div>
          </div>

          {/* Specs */}
          <div className="p-4 rounded-xl bg-[#14141B] border border-[#252533]">
            <span className="text-[10px] font-mono uppercase text-[#71717A] block">
              Resolution & Engine
            </span>
            <span className="text-sm font-semibold text-white">
              {project.result?.resolution || '1080p (1920x1080)'}
            </span>
            <span className="text-xs text-[#A1A1AA] block mt-0.5">
              Model: {project.result?.modelIdentifier || 'BollyMesh-v2.4'}
            </span>
          </div>

          {/* Provenance */}
          <div className="p-4 rounded-xl bg-[#14141B] border border-[#252533]">
            <span className="text-[10px] font-mono uppercase text-[#71717A] block">
              Digital Provenance
            </span>
            <span className="text-sm font-semibold text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="w-4 h-4" />
              C2PA Synthetic Signature
            </span>
            <span className="text-xs text-[#8E8E9E] block mt-0.5 font-mono">
              Checksum: {project.result?.checksum || 'sha256-verified'}
            </span>
          </div>
        </div>

        {/* Modal Actions Footer */}
        <div className="pt-4 border-t border-[#232330] flex items-center justify-between">
          <Button
            size="sm"
            variant="danger"
            leftIcon={<Trash2 className="w-3.5 h-3.5" />}
            onClick={() => {
              onDelete(project.id);
              onClose();
            }}
          >
            Delete Project
          </Button>

          <div className="flex items-center gap-3">
            <Button size="sm" variant="ghost" onClick={onClose}>
              Close
            </Button>
            <Button
              size="sm"
              variant="primary"
              leftIcon={<Download className="w-3.5 h-3.5" />}
              onClick={handleDownload}
            >
              Download Master MP4
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};
