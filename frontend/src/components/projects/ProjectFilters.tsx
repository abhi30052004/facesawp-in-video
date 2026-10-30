import React from 'react';
import { Search, LayoutGrid, List } from 'lucide-react';
import { ProjectStatus } from '../../types/project';

interface ProjectFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: 'all' | ProjectStatus;
  onStatusFilterChange: (status: 'all' | ProjectStatus) => void;
  viewMode: 'grid' | 'list';
  onViewModeChange: (mode: 'grid' | 'list') => void;
  totalCount: number;
}

export const ProjectFilters: React.FC<ProjectFiltersProps> = ({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  viewMode,
  onViewModeChange,
  totalCount,
}) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-[#14141B] border border-[#242432]">
      {/* Search Input */}
      <div className="relative flex-1 max-w-md">
        <Search className="w-4 h-4 text-[#71717A] absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by project title, actor, or era..."
          className="w-full bg-[#1A1A24] border border-[#2C2C3D] rounded-xl pl-10 pr-4 py-2 text-xs sm:text-sm text-white placeholder-[#71717A] focus:outline-none focus:border-[#D6AD65] transition-colors"
        />
      </div>

      {/* Status Filter Buttons & View Mode */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status Pill Filters */}
        <div className="flex p-1 bg-[#1A1A24] border border-[#2B2B3C] rounded-xl text-xs">
          {(['all', 'completed', 'processing'] as const).map((status) => (
            <button
              key={status}
              onClick={() => onStatusFilterChange(status)}
              className={`px-3 py-1.5 rounded-lg capitalize transition-all cursor-pointer ${
                statusFilter === status
                  ? 'bg-[#292938] text-white font-semibold'
                  : 'text-[#8E8E9E] hover:text-white'
              }`}
            >
              {status === 'all' ? `All (${totalCount})` : status}
            </button>
          ))}
        </div>

        {/* View Mode Toggle */}
        <div className="flex p-1 bg-[#1A1A24] border border-[#2B2B3C] rounded-xl text-xs">
          <button
            onClick={() => onViewModeChange('grid')}
            aria-label="Grid layout"
            className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === 'grid' ? 'bg-[#292938] text-white' : 'text-[#71717A] hover:text-white'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => onViewModeChange('list')}
            aria-label="List layout"
            className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === 'list' ? 'bg-[#292938] text-white' : 'text-[#71717A] hover:text-white'
            }`}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
