import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import type { ProjectTrackingResponseDto } from '../features/projects/projectService';

const ProjectTrackingPage: React.FC = () => {
  const [trackingData] = useState<ProjectTrackingResponseDto | null>(null);
  const [isLoading] = useState(false);

  useEffect(() => {
    // TODO: Fetch from projectService.getProjectTracking() once backend is ready.
    // For now, we leave it empty to avoid making fake API calls or failing network requests.
  }, []);

  return (
    <div className="min-h-[calc(100vh-65px)] bg-gray-50 p-6 flex justify-center">
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-4xl space-y-6"
      >
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Project Tracking</h1>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
             <p>Loading project tracking details...</p>
          </div>
        ) : trackingData ? (
          <div className="space-y-6">
            <Card title="Project Overview">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-100">
                  <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-1">Status</p>
                  <p className="text-sm font-medium text-zinc-900 capitalize">{trackingData.status}</p>
                </div>
                <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-100">
                  <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-1">Contractor</p>
                  <p className="text-sm font-medium text-zinc-900">{trackingData.contractorName || 'Not Assigned'}</p>
                </div>
              </div>
            </Card>

            <Card title="Construction Phases" subtitle="Track the progress of individual project phases.">
              {trackingData.phases.length > 0 ? (
                <div className="space-y-4">
                  {trackingData.phases.sort((a, b) => a.sequenceOrder - b.sequenceOrder).map((phase, index) => (
                    <div key={index} className="flex flex-col sm:flex-row sm:items-center justify-between bg-white border border-zinc-100 rounded-lg p-4 shadow-sm gap-4">
                       <div>
                         <h4 className="font-semibold text-zinc-900">{phase.sequenceOrder}. {phase.phaseName}</h4>
                         <p className="text-sm text-zinc-500 capitalize">Status: {phase.status}</p>
                       </div>
                       <div className="text-right sm:text-left text-sm text-zinc-600">
                         <p>Started: {phase.startedAtUtc ? new Date(phase.startedAtUtc).toLocaleDateString() : 'N/A'}</p>
                         <p>Completed: {phase.completedAtUtc ? new Date(phase.completedAtUtc).toLocaleDateString() : 'N/A'}</p>
                       </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-zinc-500">No phases defined yet.</p>
              )}
            </Card>
          </div>
        ) : (
          <Card className="text-center py-16">
            <div className="flex flex-col items-center gap-3">
              <h3 className="text-lg font-semibold text-zinc-900">No Tracking Data</h3>
              <p className="text-sm text-zinc-500 max-w-md mx-auto">
                Tracking information is not currently available. The project might not be approved yet, or the data is still syncing.
              </p>
              <Button variant="outline" className="mt-4" disabled>
                Refresh Data
              </Button>
            </div>
          </Card>
        )}
      </motion.div>
    </div>
  );
};

export default ProjectTrackingPage;
