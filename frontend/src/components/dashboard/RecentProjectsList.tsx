import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Film, ArrowRight, Play, Clock } from 'lucide-react';
import { FaceSwapProject } from '../../types/project';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { formatDate } from '../../utils/formatters';

interface RecentProjectsListProps {
  projects: FaceSwapProject[];
}

export const RecentProjectsList: React.FC<RecentProjectsListProps> = ({ projects }) => {
  const navigate = useNavigate();
  const recent = projects.slice(0, 3);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-cinematic font-bold text-white flex items-center gap-2">
            <Film className="w-5 h-5 text-[#D6AD65]" />
            Recent Studio Projects
          </h2>
          <p className="text-xs sm:text-sm text-[#8E8E9E]">
            Recently generated sequences, comparisons, and drafts
          </p>
        </div>

        <button
          onClick={() => navigate('/projects')}
          className="text-xs font-semibold text-[#D6AD65] hover:text-[#F4DE9C] flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <span>View All ({projects.length})</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {recent.length === 0 ? (
        <Card className="text-center py-12">
          <Film className="w-10 h-10 text-[#71717A] mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white mb-1">No Projects Found</h3>
          <p className="text-xs text-[#8E8E9E] mb-4 max-w-sm mx-auto">
            You haven't initiated any face swap renders yet. Upload your first clip to start.
          </p>
          <Button size="sm" variant="primary" onClick={() => navigate('/create')}>
            Create Your First Swap
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {recent.map((proj) => (
            <Card
              key={proj.id}
              hoverEffect
              onClick={() => navigate('/projects')}
              className="p-4 cursor-pointer group flex flex-col justify-between"
            >
              {/* Media Thumbnail */}
              <div className="aspect-video rounded-xl bg-black overflow-hidden relative mb-3">
                <img
                  src={
                    proj.targetFace?.previewUrl ||
                    'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80'
                  }
                  alt={proj.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-90"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />

                {/* Status Badge */}
                <div className="absolute top-2.5 left-2.5">
                  <Badge variant={proj.status === 'completed' ? 'emerald' : 'amber'}>
                    {proj.status === 'completed' ? 'Master Ready' : 'Processing'}
                  </Badge>
                </div>

                {/* Play hover pill */}
                <div className="absolute bottom-2.5 right-2.5 w-8 h-8 rounded-full bg-black/70 backdrop-blur-md flex items-center justify-center text-[#D6AD65] border border-[#D6AD65]/30 group-hover:scale-110 transition-transform">
                  <Play className="w-3.5 h-3.5 ml-0.5 fill-[#D6AD65]" />
                </div>
              </div>

              {/* Project Meta */}
              <div>
                <h3 className="text-sm font-cinematic font-bold text-white group-hover:text-[#D6AD65] transition-colors truncate mb-1">
                  {proj.title}
                </h3>
                <div className="flex items-center justify-between text-xs text-[#8E8E9E]">
                  <span className="flex items-center gap-1 font-mono text-[11px]">
                    <Clock className="w-3 h-3 text-[#71717A]" />
                    {formatDate(proj.createdAt)}
                  </span>
                  <span className="text-[#D6AD65] font-mono text-[11px]">
                    {proj.result?.resolution.split(' ')[0] || '1080p'}
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
