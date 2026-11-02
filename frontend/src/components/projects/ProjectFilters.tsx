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
    <div
      className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl border transition-colors duration-200"
      style={{
        backgroundColor: 'var(--bg-card)',
        borderColor: 'var(--border-card)',
      }}
    >
      {/* Search Input */}
      <div className="relative flex-1 max-w-md">
        <Search className="w-4 h-4 text-[#71717A] absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by project title, actor, or era..."
          className="w-full rounded-xl pl-10 pr-4 py-2 text-xs sm:text-sm focus:outline-none transition-colors border"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
            color: 'var(--text-primary)',
          }}
        />
      </div>

      {/* Status Filter Buttons & View Mode */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status Pill Filters */}
        <div
          className="flex p-1 rounded-xl text-xs border"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
          }}
        >
          {(['all', 'completed', 'processing'] as const).map((status) => (
            <button
              key={status}
              onClick={() => onStatusFilterChange(status)}
              className="px-3 py-1.5 rounded-lg capitalize transition-all cursor-pointer font-medium"
              style={{
                backgroundColor: statusFilter === status ? 'var(--gold)' : 'transparent',
                color: statusFilter === status ? '#09090B' : 'var(--text-secondary)',
                fontWeight: statusFilter === status ? 600 : 500,
              }}
            >
              {status === 'all' ? `All (${totalCount})` : status}
            </button>
          ))}
        </div>

        {/* View Mode Toggle */}
        <div
          className="flex p-1 rounded-xl text-xs border"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border)',
          }}
        >
          <button
            onClick={() => onViewModeChange('grid')}
            aria-label="Grid layout"
            className="p-1.5 rounded-lg transition-colors cursor-pointer"
            style={{
              backgroundColor: viewMode === 'grid' ? 'var(--gold)' : 'transparent',
              color: viewMode === 'grid' ? '#09090B' : 'var(--text-muted)',
            }}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => onViewModeChange('list')}
            aria-label="List layout"
            className="p-1.5 rounded-lg transition-colors cursor-pointer"
            style={{
              backgroundColor: viewMode === 'list' ? 'var(--gold)' : 'transparent',
              color: viewMode === 'list' ? '#09090B' : 'var(--text-muted)',
            }}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
