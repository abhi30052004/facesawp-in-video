import React from 'react';
import { Play, Trash2, Clock, Eye } from 'lucide-react';
import { FaceSwapProject } from '../../types/project';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { formatDate, formatDuration } from '../../utils/formatters';

interface ProjectCardProps {
  project: FaceSwapProject;
  onSelect: (project: FaceSwapProject) => void;
  onDelete: (id: string) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project, onSelect, onDelete }) => {
  return (
    <Card hoverEffect className="p-4 flex flex-col justify-between group">
      <div>
        {/* Thumbnail Preview Area */}
        <div
          onClick={() => onSelect(project)}
          className="aspect-video rounded-xl bg-black overflow-hidden relative mb-3 cursor-pointer group/thumb"
        >
          <img
            src={
              project.targetFace?.previewUrl ||
              'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80'
            }
            alt={project.title}
            className="w-full h-full object-cover group-hover/thumb:scale-105 transition-transform duration-500"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />

          {/* Status Badge */}
          <div className="absolute top-2.5 left-2.5">
            <Badge variant={project.status === 'completed' ? 'emerald' : 'amber'}>
              {project.status === 'completed' ? 'Completed' : 'Processing'}
            </Badge>
          </div>

          {/* Duration Badge */}
          {project.sourceVideo?.durationSec && (
            <div className="absolute bottom-2.5 left-2.5 bg-black/80 px-2 py-0.5 rounded text-[10px] font-mono text-white border border-white/10">
              {formatDuration(project.sourceVideo.durationSec)}
            </div>
          )}

          {/* Hover Play Button */}
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover/thumb:opacity-100 transition-opacity bg-black/40">
            <div className="w-11 h-11 rounded-full bg-[#D6AD65] text-[#09090B] flex items-center justify-center font-bold shadow-xl">
              <Play className="w-5 h-5 ml-0.5 fill-[#09090B]" />
            </div>
          </div>
        </div>

        {/* Title & Target Persona */}
        <div className="mb-3">
          <h3
            onClick={() => onSelect(project)}
            className="text-base font-cinematic font-bold text-white group-hover:text-[#D6AD65] transition-colors truncate cursor-pointer"
          >
            {project.title}
          </h3>
          <p className="text-xs text-[#A1A1AA] flex items-center gap-1.5 mt-0.5">
            <span>Target:</span>
            <span className="text-[#D6AD65] font-medium truncate">
              {project.targetFace?.name || 'Custom Persona'}
            </span>
          </p>
        </div>
      </div>

      {/* Footer Meta & Actions */}
      <div className="pt-3 border-t border-[#252535] flex items-center justify-between text-xs text-[#8E8E9E]">
        <div className="flex items-center gap-1 font-mono text-[11px]">
          <Clock className="w-3.5 h-3.5 text-[#71717A]" />
          <span>{formatDate(project.createdAt)}</span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onSelect(project)}
            aria-label="Inspect project"
            className="p-1.5 rounded-lg text-[#A1A1AA] hover:text-[#D6AD65] hover:bg-[#1E1E28] transition-colors cursor-pointer"
          >
            <Eye className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(project.id);
            }}
            aria-label="Delete project"
            className="p-1.5 rounded-lg text-[#A1A1AA] hover:text-red-400 hover:bg-[#1E1E28] transition-colors cursor-pointer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Card>
  );
};
