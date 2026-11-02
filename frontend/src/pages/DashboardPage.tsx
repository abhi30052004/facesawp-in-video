import React from 'react';
import { QuickActionHero } from '../components/dashboard/QuickActionHero';
import { HowItWorksGuide } from '../components/dashboard/HowItWorksGuide';
import { RecentProjectsList } from '../components/dashboard/RecentProjectsList';
import { useProjects } from '../context/ProjectContext';

export const DashboardPage: React.FC = () => {
  const { projects } = useProjects();

  return (
    <div className="space-y-10 pb-12">
      {/* Hero Banner with CTA */}
      <QuickActionHero />

      {/* Recent Projects */}
      <RecentProjectsList projects={projects} />

      {/* How it Works */}
      <HowItWorksGuide />
    </div>
  );
};
