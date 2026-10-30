import React from 'react';
import { Zap, Film, Clock, HardDrive } from 'lucide-react';
import { QuickActionHero } from '../components/dashboard/QuickActionHero';
import { StatCard } from '../components/dashboard/StatCard';
import { HowItWorksGuide } from '../components/dashboard/HowItWorksGuide';
import { RecentProjectsList } from '../components/dashboard/RecentProjectsList';
import { useProjects } from '../context/ProjectContext';

export const DashboardPage: React.FC = () => {
  const { stats, projects } = useProjects();

  return (
    <div className="space-y-10 pb-12">
      {/* Directorial Hero Banner with Prominent CTA */}
      <QuickActionHero />

      {/* Usage Statistics Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-cinematic font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-[#D6AD65]" />
              Studio Usage & Compute Quota
            </h2>
            <p className="text-xs sm:text-sm text-[#8E8E9E]">
              Current billing cycle allocation and GPU cluster capacity
            </p>
          </div>
          <span className="text-xs font-mono text-[#D6AD65] bg-[#D6AD65]/10 px-3 py-1 rounded-full border border-[#D6AD65]/30">
            Renews: {stats.renewalDate}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Render Credits"
            value={`${stats.creditsRemaining}`}
            subtext={`of ${stats.creditsTotal} monthly credits remaining`}
            icon={<Zap className="w-5 h-5" />}
            color="gold"
            trend="Active Tier"
          />

          <StatCard
            label="Swaps Rendered"
            value={stats.totalSwapsRendered}
            subtext="Total completed master sequences"
            icon={<Film className="w-5 h-5" />}
            color="burgundy"
            trend="+12 this week"
          />

          <StatCard
            label="Footage Processed"
            value={`${stats.minutesProcessed}m`}
            subtext="Total synthesized cinematic duration"
            icon={<Clock className="w-5 h-5" />}
            color="slate"
          />

          <StatCard
            label="Studio Storage"
            value={`${(stats.storageUsedMb / 1024).toFixed(1)} GB`}
            subtext={`of ${(stats.storageLimitMb / 1024).toFixed(0)} GB high-speed cloud cache`}
            icon={<HardDrive className="w-5 h-5" />}
            color="emerald"
            trend="Healthy"
          />
        </div>
      </section>

      {/* Recent Projects Roster */}
      <RecentProjectsList projects={projects} />

      {/* How it Works Section */}
      <HowItWorksGuide />
    </div>
  );
};
