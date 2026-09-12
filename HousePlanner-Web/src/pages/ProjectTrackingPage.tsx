import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import projectService, { type ProjectTrackingResponseDto } from '../features/projects/projectService';

const ProjectTrackingPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryProjectId = searchParams.get('projectId');
  const queryWorkflowId = searchParams.get('workflowId');

  const [inputProjectId, setInputProjectId] = useState(queryProjectId || '');
  const [trackingData, setTrackingData] = useState<ProjectTrackingResponseDto | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchTracking = useCallback(async (pId?: string, wId?: string) => {
    const targetProjectId = pId || queryProjectId;
    const targetWorkflowId = wId || queryWorkflowId;

    if (!targetProjectId && !targetWorkflowId) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      let data: ProjectTrackingResponseDto;
      if (targetProjectId) {
        data = await projectService.getProjectTracking(targetProjectId);
      } else {
        data = await projectService.getProjectByWorkflow(targetWorkflowId!);
      }
      setTrackingData(data);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } }; message?: string };
      setErrorMessage(error.response?.data?.message || error.message || 'Project not found or status unavailable.');
      setTrackingData(null);
    } finally {
      setIsLoading(false);
    }
  }, [queryProjectId, queryWorkflowId]);

  useEffect(() => {
    if (queryProjectId || queryWorkflowId) {
      fetchTracking();
    }
  }, [queryProjectId, queryWorkflowId, fetchTracking]);

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedId = inputProjectId.trim();
    if (trimmedId) {
      navigate(`/project-tracking?projectId=${trimmedId}`);
    }
  };

  return (
    <div className="min-h-[calc(100vh-65px)] bg-gray-50 p-6 flex justify-center">
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-4xl space-y-6"
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Project Status & Handoff</h1>
            <p className="text-xs text-zinc-500 mt-1">Component D: Post-approval project handoff & status</p>
          </div>
          {trackingData && (
            <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
              trackingData.status === 'not_started' ? 'bg-amber-100 text-amber-800' :
              trackingData.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
              trackingData.status === 'completed' ? 'bg-emerald-100 text-emerald-800' :
              'bg-zinc-100 text-zinc-800'
            }`}>
              {trackingData.status.replace('_', ' ')}
            </span>
          )}
        </div>

        {/* Project Lookup Bar */}
        <Card title="Project Lookup" subtitle="Inspect the status of an approved project using its Project ID.">
          <form onSubmit={handleLookup} className="flex gap-3">
            <input
              type="text"
              placeholder="Enter Project ID (GUID)..."
              value={inputProjectId}
              onChange={(e) => setInputProjectId(e.target.value)}
              className="flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <Button variant="primary" type="submit" disabled={!inputProjectId.trim() || isLoading}>
              {isLoading ? 'Searching...' : 'Search'}
            </Button>
          </form>
        </Card>

        {errorMessage && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
            <span className="font-semibold">Notice:</span> {errorMessage}
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
            <p>Loading project details...</p>
          </div>
        ) : trackingData ? (
          <div className="space-y-6">
            <Card title="Approved Project Status">
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-100">
                    <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-1">Project ID</p>
                    <p className="text-xs font-mono text-zinc-900 break-all">{trackingData.projectId}</p>
                  </div>
                  <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-100">
                    <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-1">Registration Status</p>
                    <p className="text-sm font-medium text-zinc-900 capitalize">{trackingData.status.replace('_', ' ')}</p>
                  </div>
                </div>

                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-900 text-sm">
                  <p className="font-semibold">✓ Project Successfully Registered</p>
                  <p className="text-xs text-emerald-700 mt-1">
                    The house planning workflow has passed deterministic safety validation and received human approval. The project record is persisted in the database.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        ) : (
          <Card className="text-center py-16">
            <div className="flex flex-col items-center gap-3">
              <h3 className="text-lg font-semibold text-zinc-900">No Project Selected</h3>
              <p className="text-sm text-zinc-500 max-w-md mx-auto">
                Please enter a Project ID above, or complete the Human Approval workflow to create and view an approved project.
              </p>
              <Button variant="outline" onClick={() => navigate('/approval')} className="mt-2 text-xs">
                Go to Project Approval →
              </Button>
            </div>
          </Card>
        )}
      </motion.div>
    </div>
  );
};

export default ProjectTrackingPage;
