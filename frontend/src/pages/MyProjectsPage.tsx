import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Film, Plus, Sparkles, Trash2, Eye } from 'lucide-react';
import { useProjects } from '../context/ProjectContext';
import { ProjectCard } from '../components/projects/ProjectCard';
import { ProjectFilters } from '../components/projects/ProjectFilters';
import { ProjectDetailModal } from '../components/projects/ProjectDetailModal';
import { FaceSwapProject, ProjectStatus } from '../types/project';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { formatDate } from '../utils/formatters';

export const MyProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const { projects, deleteProject } = useProjects();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | ProjectStatus>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedProject, setSelectedProject] = useState<FaceSwapProject | null>(null);

  const filteredProjects = projects.filter((project) => {
    const matchesSearch =
      project.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.targetFace?.name.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-cinematic font-bold text-white flex items-center gap-2.5">
            <Film className="w-6 h-6 text-[#D6AD65]" />
            Studio Film Roster & Archive
          </h1>
          <p className="text-xs sm:text-sm text-[#8E8E9E]">
            Inspect, compare, and export previously rendered face swap sequences
          </p>
        </div>

        <Button
          size="md"
          variant="primary"
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={() => navigate('/create')}
        >
          New Face Swap
        </Button>
      </div>

      {/* Filters & Search Control Bar */}
      <ProjectFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        totalCount={projects.length}
      />

      {/* Empty State */}
      {filteredProjects.length === 0 ? (
        <Card className="text-center py-16 px-4">
          <Film className="w-12 h-12 text-[#71717A] mx-auto mb-3" />
          <h3 className="text-lg font-cinematic font-bold text-white mb-1">
            No Cinematic Sequences Found
          </h3>
          <p className="text-xs sm:text-sm text-[#8E8E9E] max-w-md mx-auto mb-6">
            {searchQuery
              ? `No projects matched "${searchQuery}". Try adjusting your keywords or clearing the filter.`
              : 'Your studio film archive is currently empty. Initiate your first neural face swap to populate your roster.'}
          </p>
          <Button
            size="md"
            variant="primary"
            leftIcon={<Sparkles className="w-4 h-4" />}
            onClick={() => navigate('/create')}
          >
            Create Face Swap
          </Button>
        </Card>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onSelect={setSelectedProject}
              onDelete={deleteProject}
            />
          ))}
        </div>
      ) : (
        /* List View */
        <div className="bg-[#14141B] border border-[#242432] rounded-2xl overflow-hidden divide-y divide-[#22222E]">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              onClick={() => setSelectedProject(project)}
              className="p-4 flex items-center justify-between gap-4 hover:bg-[#181822] transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-4 min-w-0">
                <img
                  src={
                    project.targetFace?.previewUrl ||
                    'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80'
                  }
                  alt={project.title}
                  className="w-16 h-10 rounded-lg object-cover border border-[#2E2E3E] shrink-0"
                />
                <div className="min-w-0">
                  <h4 className="text-sm font-cinematic font-bold text-white group-hover:text-[#D6AD65] transition-colors truncate">
                    {project.title}
                  </h4>
                  <div className="flex items-center gap-3 text-xs text-[#8E8E9E]">
                    <span>Actor: {project.targetFace?.name || 'Persona'}</span>
                    <span>•</span>
                    <span className="font-mono">{formatDate(project.createdAt)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <Badge variant={project.status === 'completed' ? 'emerald' : 'amber'}>
                  {project.status === 'completed' ? 'Master Ready' : 'Processing'}
                </Badge>

                <span className="text-xs font-mono text-[#D6AD65] hidden sm:inline">
                  {project.result?.resolution.split(' ')[0] || '1080p'}
                </span>

                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedProject(project);
                    }}
                    className="p-1.5 rounded-lg text-[#A1A1AA] hover:text-[#D6AD65] transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteProject(project.id);
                    }}
                    className="p-1.5 rounded-lg text-[#A1A1AA] hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Project Detail Modal */}
      <ProjectDetailModal
        project={selectedProject}
        isOpen={!!selectedProject}
        onClose={() => setSelectedProject(null)}
        onDelete={deleteProject}
      />
    </div>
  );
};
