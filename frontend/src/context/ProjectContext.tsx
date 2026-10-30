import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { FaceSwapProject, TargetFaceSelection, VideoMetadata } from '../types/project';
import { StudioUsageStats } from '../types/api';
import { bollySwapApi } from '../services/api';
import { INITIAL_MOCK_STATS } from '../services/mockData';

interface WizardDraft {
  step: 'video' | 'face' | 'consent' | 'processing' | 'results';
  title: string;
  sourceVideo?: VideoMetadata;
  targetFace?: TargetFaceSelection;
  configuration: {
    faceEnhance: boolean;
    colorHarmony: boolean;
    temporalConsistency: boolean;
    resolutionTarget: '720p' | '1080p' | '4k';
    cinematicGrade: 'authentic' | 'warm-vintage' | 'vibrant-masala' | 'moody-noir';
    watermarkEnabled: boolean;
  };
  consentGranted: boolean;
  activeProjectId?: string;
}

const DEFAULT_WIZARD_DRAFT: WizardDraft = {
  step: 'video',
  title: 'Cinematic Sequence #01',
  configuration: {
    faceEnhance: true,
    colorHarmony: true,
    temporalConsistency: true,
    resolutionTarget: '1080p',
    cinematicGrade: 'authentic',
    watermarkEnabled: true,
  },
  consentGranted: false,
};

interface ProjectContextType {
  projects: FaceSwapProject[];
  stats: StudioUsageStats;
  wizardDraft: WizardDraft;
  isLoading: boolean;
  updateWizardDraft: (update: Partial<WizardDraft>) => void;
  resetWizardDraft: () => void;
  saveCurrentProject: (project: FaceSwapProject) => void;
  deleteProject: (id: string) => void;
  refreshProjects: () => Promise<void>;
  deductCreditForRender: () => void;
}

const ProjectContext = createContext<ProjectContextType | null>(null);

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [projects, setProjects] = useState<FaceSwapProject[]>([]);
  const [stats, setStats] = useState<StudioUsageStats>(INITIAL_MOCK_STATS);
  const [wizardDraft, setWizardDraft] = useState<WizardDraft>(DEFAULT_WIZARD_DRAFT);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshProjects = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await bollySwapApi.getProjects();
      const currentStats = await bollySwapApi.getStudioUsageStats();
      setProjects(list);
      setStats(currentStats);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  const updateWizardDraft = (update: Partial<WizardDraft>) => {
    setWizardDraft((prev) => ({ ...prev, ...update }));
  };

  const resetWizardDraft = () => {
    setWizardDraft({
      ...DEFAULT_WIZARD_DRAFT,
      title: `Cinematic Sequence #${(projects.length + 1).toString().padStart(2, '0')}`,
    });
  };

  const saveCurrentProject = (project: FaceSwapProject) => {
    bollySwapApi.saveProjectLocally(project);
    setProjects((prev) => {
      const idx = prev.findIndex((p) => p.id === project.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = project;
        return next;
      }
      return [project, ...prev];
    });
  };

  const deleteProject = (id: string) => {
    bollySwapApi.deleteProjectLocally(id);
    setProjects((prev) => prev.filter((p) => p.id !== id));
  };

  const deductCreditForRender = () => {
    setStats((prev) => {
      const updated: StudioUsageStats = {
        ...prev,
        creditsRemaining: Math.max(0, prev.creditsRemaining - 10),
        totalSwapsRendered: prev.totalSwapsRendered + 1,
        minutesProcessed: parseFloat((prev.minutesProcessed + 0.25).toFixed(2)),
        storageUsedMb: prev.storageUsedMb + 45,
      };
      localStorage.setItem('bollyswap_stats_v1', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <ProjectContext.Provider
      value={{
        projects,
        stats,
        wizardDraft,
        isLoading,
        updateWizardDraft,
        resetWizardDraft,
        saveCurrentProject,
        deleteProject,
        refreshProjects,
        deductCreditForRender,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProjects = () => {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProjects must be used within a ProjectProvider');
  }
  return context;
};

