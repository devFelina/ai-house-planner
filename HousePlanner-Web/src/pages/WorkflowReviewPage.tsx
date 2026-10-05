import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { workflowService, type WorkflowStatusResponseDto } from '../services/workflowService';
import { FloorPlanViewer, type FloorPlanData } from '../components/floorplan/FloorPlanViewer';
import { Edit2, Trash2, Plus, Save, X, CheckCircle, Clock } from 'lucide-react';
import { AgentTimeline } from '../components/AgentTimeline';
import useAuth from '../features/auth/useAuth';
import { formatFloorName, formatRoomName } from '../utils/presentation';
import { SHOW_TECHNICAL_PLAN } from '../config/features';

const safeDisplayValue = (val: any): string => {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
};

export const WorkflowReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const previewDesignId = searchParams.get('design') || undefined;
  const [workflow, setWorkflow] = useState<WorkflowStatusResponseDto | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<'floorplan' | 'construction'>('floorplan');
  const [visualizationData, setVisualizationData] = useState<any>(null);

  useEffect(() => {
    const designId = workflow?.design?.designId;
    if (!designId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const loadVisualization = async () => {
      try {
        const result = await workflowService.getDesignVisualization(designId);
        if (cancelled) return;
        setVisualizationData(result);
        if (result.status === 'generating') timer = setTimeout(loadVisualization, 3000);
      } catch {
        if (!cancelled) setVisualizationData({ status: 'failed', imageUrl: null });
      }
    };
    setVisualizationData(null);
    loadVisualization();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [workflow?.design?.designId]);

  const { user } = useAuth();
  const isAdmin = user?.role === 'Admin' || user?.role === 'Constructor';
  const showTechnicalPlan = SHOW_TECHNICAL_PLAN || Boolean(user && user.role !== 'Customer');
  const [isEditingPlan, setIsEditingPlan] = useState(false);
  const [editTargetDuration, setEditTargetDuration] = useState<number | ''>('');
  const [editScheduleStatus, setEditScheduleStatus] = useState<string>('ON_SCHEDULE');
  const [isSavingPlan, setIsSavingPlan] = useState(false);
  const [editingPhaseId, setEditingPhaseId] = useState<number | null>(null);
  const [phaseFormData, setPhaseFormData] = useState<any>({});
  const [isAddingPhase, setIsAddingPhase] = useState(false);

  const [isSubmittingToArchitect, setIsSubmittingToArchitect] = useState(false);
  const [submitArchitectSuccess, setSubmitArchitectSuccess] = useState(false);
  const [submitArchitectError, setSubmitArchitectError] = useState('');

  const handleSendToArchitect = async () => {
    if (!id || !workflow?.design?.designId) return;
    setIsSubmittingToArchitect(true);
    setSubmitArchitectError('');
    setSubmitArchitectSuccess(false);
    try {
      await workflowService.submitArchitectReview(id, workflow.design.designId);
      setSubmitArchitectSuccess(true);
      setWorkflow({ ...workflow, status: 'awaiting_architect_review' });
      setTimeout(() => setSubmitArchitectSuccess(false), 4000);
    } catch (err: any) {
      setSubmitArchitectError(err?.response?.data?.message || err.message || 'Failed to submit design.');
    } finally {
      setIsSubmittingToArchitect(false);
    }
  };

  const startEditingPlan = () => {
    if (!workflow?.constructionPlan) return;
    setEditTargetDuration(workflow.constructionPlan.project_summary.target_duration_days || '');
    setEditScheduleStatus(workflow.constructionPlan.project_summary.schedule_status || 'ON_SCHEDULE');
    setIsEditingPlan(true);
  };

  const handleSavePlan = async () => {
    if (!id || !workflow?.constructionPlan) return;
    setIsSavingPlan(true);
    try {
      const updatedPlan = {
        ...workflow.constructionPlan,
        project_summary: {
          ...workflow.constructionPlan.project_summary,
          target_duration_days: editTargetDuration === '' ? null : Number(editTargetDuration),
          schedule_status: editScheduleStatus
        }
      };
      await workflowService.updateConstructionPlan(id, updatedPlan);
      setWorkflow(prev => prev ? { ...prev, constructionPlan: updatedPlan } : prev);
      setIsEditingPlan(false);
    } catch (e: any) {
      alert(e.response?.data?.message || 'Error updating plan');
    } finally {
      setIsSavingPlan(false);
    }
  };

  const startEditingPhase = (phase: any) => {
    setEditingPhaseId(phase.id);
    setPhaseFormData({ ...phase });
  };

  const startAddingPhase = () => {
    const nextId = workflow?.constructionPlan?.phases?.length
      ? Math.max(...workflow.constructionPlan.phases.map((p: any) => p.id)) + 1
      : 1;
    setPhaseFormData({ id: nextId, name: '', start_day: 1, end_day: 1, duration_days: 1, depends_on: [] });
    setIsAddingPhase(true);
  };

  const cancelPhaseEdit = () => {
    setEditingPhaseId(null);
    setIsAddingPhase(false);
    setPhaseFormData({});
  };

  const savePhase = async () => {
    if (!id || !workflow?.constructionPlan) return;
    setIsSavingPlan(true);
    try {
      let updatedPhases = [...workflow.constructionPlan.phases];
      if (isAddingPhase) {
        updatedPhases.push(phaseFormData);
      } else {
        const index = updatedPhases.findIndex((p: any) => p.id === phaseFormData.id);
        if (index > -1) updatedPhases[index] = phaseFormData;
      }

      updatedPhases.sort((a: any, b: any) => a.start_day - b.start_day); // Keep chronological

      const updatedPlan = { ...workflow.constructionPlan, phases: updatedPhases };
      await workflowService.updateConstructionPlan(id, updatedPlan);
      setWorkflow(prev => prev ? { ...prev, constructionPlan: updatedPlan } : prev);
      cancelPhaseEdit();
    } catch (e: any) {
      alert(e.response?.data?.message || 'Error saving phase');
    } finally {
      setIsSavingPlan(false);
    }
  };

  const deletePhase = async (phaseId: number) => {
    if (!id || !workflow?.constructionPlan) return;
    if (!confirm('Are you sure you want to delete this phase?')) return;
    setIsSavingPlan(true);
    try {
      const updatedPhases = workflow.constructionPlan.phases.filter((p: any) => p.id !== phaseId);
      const updatedPlan = { ...workflow.constructionPlan, phases: updatedPhases };
      await workflowService.updateConstructionPlan(id, updatedPlan);
      setWorkflow(prev => prev ? { ...prev, constructionPlan: updatedPlan } : prev);
    } catch (e: any) {
      alert(e.response?.data?.message || 'Error deleting phase');
    } finally {
      setIsSavingPlan(false);
    }
  };

  useEffect(() => {
    if (!id) return;

    let interval: ReturnType<typeof setInterval>;
    let error404Count = 0;

    const fetchWorkflow = async () => {
      try {
        const data = await workflowService.getWorkflowStatus(id, previewDesignId);
        setWorkflow(data);
        setError(null);
        setLoading(false);
        error404Count = 0;

        // If the status is no longer running, we can stop polling
        if (data.status !== 'running' && data.status !== 'pending') {
          clearInterval(interval);
        }
      } catch (err: any) {
        if (err.response?.status === 404 || err.message?.includes('404')) {
          error404Count++;
          if (error404Count >= 5) {
            setError('Workflow not found. It may have failed to save or you do not have permission.');
            setLoading(false);
            clearInterval(interval);
          } else {
            setError(null);
          }
        } else {
          setError(err.message || 'Failed to fetch workflow status');
          setLoading(false);
          clearInterval(interval);
        }
      }
    };

    fetchWorkflow();
    interval = setInterval(() => { fetchWorkflow(); }, 3000);
    return () => clearInterval(interval);
  }, [id, previewDesignId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-65px)] bg-gradient-to-br from-slate-50 to-zinc-100">
        <div className="text-center p-4 md:p-8 bg-surface/60 backdrop-blur-md rounded-2xl shadow-sm border border-white">
          <div className="relative inline-block mb-4">
            <div className="w-12 h-12 border-4 border-indigo-200 rounded-full"></div>
            <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin absolute top-0 left-0"></div>
          </div>
          <p className="text-text-secondary font-medium tracking-wide">Loading design environment...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-65px)] bg-gradient-to-br from-red-50 to-red-100/50">
        <div className="bg-surface/80 backdrop-blur-xl p-4 md:p-10 rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-red-100 max-w-md text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner">
            <div className="text-red-500 text-2xl md:text-3xl font-bold">!</div>
          </div>
          <h2 className="text-2xl font-bold text-zinc-900 mb-3 tracking-tight">Error Loading Design</h2>
          <p className="text-red-600 text-sm font-medium bg-red-50 p-4 rounded-xl">{error}</p>
        </div>
      </div>
    );
  }

  if (workflow?.status === 'failed') {
    let failureData = null;
    try {
      failureData = JSON.parse(workflow.failureReason || '');
    } catch {
      // Ignored
    }

    if (failureData?.code === 'BUILDABLE_ENVELOPE_VIOLATION') {
      return <div role="alert" className="p-4 md:p-8 max-w-xl mx-auto text-center mt-10 bg-surface rounded-3xl shadow-sm border border-border">
        <h2 className="text-2xl font-bold text-red-600 mb-3">Design generation could not complete</h2>
        <p className="text-text-secondary mb-6">{failureData.message}</p>
        <div className="flex justify-center gap-4">
          <Link to="/dashboard/new-project" className="px-5 py-2.5 rounded-xl border border-zinc-300 font-bold hover:bg-surface-elevated">Edit Land Details</Link>
        </div>
        <AgentTimeline agentExecutionLog={workflow?.agentExecutionLog} />
      </div>;
    }

    return <div role="alert" className="p-4 md:p-8 text-center mt-10 max-w-md mx-auto bg-surface rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-red-100">
      <h2 className="text-2xl font-bold text-red-600 mb-3">Design generation could not complete</h2>
      <p className="text-text-secondary">{workflow.failureReason || (workflow.terrainType === 'unknown'
        ? 'Provide a manual terrain classification and submit again.'
        : 'No valid layout was saved. Review plot dimensions and room requirements, then submit again.')}</p>
      <Link to="/dashboard/new-project" className="mt-6 inline-flex px-5 py-2.5 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-700">
        Try Again
      </Link>
      <AgentTimeline agentExecutionLog={workflow?.agentExecutionLog} />
    </div>;
  }

  if (!workflow || !workflow.design) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-65px)] bg-gradient-to-br from-slate-50 to-zinc-100 relative overflow-hidden">
        <div className="absolute top-1/4 right-1/3 w-full max-w-64 h-64 bg-indigo-200/40 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob"></div>
        <div className="bg-surface/90 backdrop-blur-xl p-4 md:p-12 rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white/60 max-w-md text-center relative z-10">
          <div className="w-20 h-20 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-inner border border-indigo-100/50">
            <span className="text-2xl md:text-4xl">🏗️</span>
          </div>
          <h2 className="text-2xl font-bold text-zinc-900 mb-3 tracking-tight">Design In Progress</h2>
          <p className="text-text-muted text-sm leading-relaxed mb-6 font-medium">
            The AI Architect is actively computing geometries and generating your house layout. This page will update automatically.
          </p>
          <div className="inline-flex items-center gap-2 bg-surface-muted/80 px-4 py-2 rounded-full border border-border/50">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
            </span>
            <p className="text-xs text-text-secondary font-bold uppercase tracking-wider">{workflow?.status?.replace(/_/g, ' ') || 'initializing'}</p>
          </div>
          <AgentTimeline agentExecutionLog={workflow?.agentExecutionLog} />
        </div>
      </div>
    );
  }

  const floorPlanData: FloorPlanData = {
    design_id: workflow.design.designId,
    floor_count: workflow.design.floorCount,
    total_built_up_area_sqft: workflow.design.totalBuiltUpAreaSqft,
    entrances: workflow.design.entrances,
    rooms: workflow.design.rooms.map(r => ({
      room_id: r.roomId,
      room_type: r.roomType,
      name: r.name || undefined,
      floor: r.floorNumber,
      x: r.x,
      y: r.y,
      width: r.width,
      length: r.length,
      wall_height: r.wallHeight,
      doors: r.doors || [],
      windows: r.windows || []
    }))
  };

  const floorNumbers = Array.from({ length: workflow.design.floorCount }, (_, i) => i + 1);
  // Customer actions (approve/reject are architect-only; we don't show them here)


  const bedroomCount = workflow.design.rooms.filter(r => r.roomType?.toLowerCase() === "bedroom").length;
  const bathroomCount = workflow.design.rooms.filter(r => r.roomType?.toLowerCase() === "bathroom").length;

  console.log("Extracted generated rooms:", workflow.design.rooms);

  console.log("WORKFLOW RESPONSE", workflow);



  return (
    <div className="min-h-[calc(100vh-65px)] bg-slate-50 text-zinc-900">
      <div className="max-w-6xl mx-auto px-4 py-4 md:py-8">
        {/* Tabs for Design vs Construction Plan */}
        <div className="flex gap-2 mb-6 bg-slate-200/50 p-1.5 rounded-xl w-fit">
          <button
            onClick={() => setActiveTab('floorplan')}
            className={`px-4 md:px-6 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'floorplan' ? 'bg-white text-indigo-600 shadow-sm' : 'text-text-muted hover:text-slate-700'
              }`}
          >
            Architectural Review
          </button>
          <button
            onClick={() => setActiveTab('construction')}
            className={`px-4 md:px-6 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${activeTab === 'construction' ? 'bg-white text-indigo-600 shadow-sm' : 'text-text-muted hover:text-slate-700'
              }`}
          >
            🚧 Construction Plan
          </button>
        </div>

        {activeTab === 'floorplan' ? (
          <div className="space-y-8 animate-fade-in">

            {/* Section A: AI Home Design */}
            <section className="bg-white rounded-3xl p-4 md:p-6 md:p-8 shadow-sm border border-slate-200">
              <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <div>
                  <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">Architectural Visualization Preview</h1>
                  <p className="text-slate-500 mt-1">This image is a visual rendering generated from the validated deterministic floor plan.</p>
                </div>
                <div className="flex items-center gap-3">
                  {submitArchitectSuccess && <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200 shadow-sm">Sent to Architect!</span>}
                  {submitArchitectError && <span className="text-sm font-bold text-red-600 bg-red-50 px-3 py-1.5 rounded-xl border border-red-200 shadow-sm">{submitArchitectError}</span>}

                  {!['awaiting_architect_review', 'approved'].includes(workflow.status) && workflow.architectReviewStatus !== 'Rejected' && (
                    <button
                      onClick={handleSendToArchitect}
                      disabled={isSubmittingToArchitect}
                      className="px-5 py-2 bg-indigo-600 text-white text-sm font-bold rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50 shadow-sm"
                    >
                      {isSubmittingToArchitect ? 'Sending...' : 'Send to Architect'}
                    </button>
                  )}
                </div>
              </div>

              <div className="bg-zinc-950 rounded-2xl overflow-hidden shadow-inner min-h-[400px] flex items-center justify-center relative">
                {visualizationData?.status === 'completed' && visualizationData?.imageUrl ? (
                  <img src={visualizationData.imageUrl} alt="AI Visualization" className="w-full max-h-[600px] object-contain" />
                ) : visualizationData?.status === 'generating' || visualizationData === null ? (
                  <div className="text-zinc-500 flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-4 border-zinc-800 border-t-indigo-500 rounded-full animate-spin"></div>
                    <span className="text-sm font-medium">Generating AI visualization...</span>
                  </div>
                ) : (
                  <div className="text-zinc-400 flex flex-col items-center gap-2 text-center p-4 md:p-6">
                    <span className="text-lg font-bold text-zinc-300">AI visualization unavailable</span>
                    <span className="text-sm">Your validated deterministic floor plan is available below.</span>
                  </div>
                )}
              </div>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-8">
              {/* Section B: Your Request */}
              <section className="bg-white rounded-3xl p-4 md:p-6 md:p-8 shadow-sm border border-slate-200 h-fit">
                <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                  <span className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">📋</span>
                  Your Home Requirements
                </h2>
                <div className="space-y-4 text-sm">
                  <div className="flex justify-between items-center py-3 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Land Size</span>
                    <span className="font-bold">
                      {workflow.requirements?.landSizePerches
                        ? `${workflow.requirements.landSizePerches} perches${workflow.requirements.landSizeCategory ? ` (${workflow.requirements.landSizeCategory} Plot)` : ''}`
                        : 'Data unavailable'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-3 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">House Type</span>
                    <span className="font-bold capitalize">{workflow.requirements?.houseType ?? 'Data unavailable'}</span>
                  </div>
                  <div className="flex justify-between items-center py-3">
                    <span className="text-slate-500 font-medium">Floors</span>
                    <span className="font-bold">{workflow.requirements?.floors ?? 'Data unavailable'}</span>
                  </div>
                </div>


                <div className="space-y-4 text-sm">
                  <div className="flex justify-between items-center py-3 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Bedrooms</span>
                    <span className="font-bold">{bedroomCount}</span>
                  </div>
                  <div className="flex justify-between items-center py-3">
                    <span className="text-slate-500 font-medium">Bathrooms</span>
                    <span className="font-bold">{bathroomCount}</span>
                  </div>
                </div>
              </section>

              {/* Section C: Generated Design */}
              <section className="bg-white rounded-3xl p-4 md:p-6 md:p-8 shadow-sm border border-slate-200 h-fit">
                <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                  <span className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-500">✨</span>
                  Generated Floor Plan
                </h2>
                <p className="text-sm text-slate-500 mb-6">Created by deterministic spatial planning engine</p>
                <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 max-h-80 overflow-y-auto">
                  <ul className="space-y-4">
                    {workflow.design?.rooms.map(r => (
                      <li key={r.roomId} className="flex flex-col gap-1 p-3 bg-white border border-slate-100 rounded-xl shadow-sm">
                        <span className="font-bold text-slate-800">{r.name || formatRoomName(r.roomType)}</span>
                        <span className="text-sm text-slate-600">Size: {r.width} ft × {r.length} ft</span>
                        <span className="text-xs text-slate-400 font-mono">Coordinates: X: {r.x} Y: {r.y}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            </div>

            {/* Section D: Architect / Developer View */}
            {showTechnicalPlan && (
              <section className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
                <details className="group">
                  <summary className="p-4 md:p-6 md:p-8 cursor-pointer list-none flex items-center justify-between font-bold text-xl hover:bg-slate-50 transition-colors focus-visible:outline-none">
                    <div className="flex items-center gap-2">
                      <span className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-white text-sm">📐</span>
                      Architect / Developer View
                    </div>
                    <span className="text-slate-400 group-open:rotate-180 transition-transform duration-300">▼</span>
                  </summary>

                  <div className="p-4 md:p-6 md:p-8 border-t border-slate-100 bg-slate-50">
                    <p className="text-sm text-slate-500 mb-6">Deterministic geometry generated from LayoutJson.</p>

                    <div className="overflow-x-auto bg-white rounded-xl border border-slate-200 shadow-sm mb-8">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-slate-100 text-slate-600">
                          <tr>
                            <th className="p-4 font-bold border-b border-slate-200">Room Name</th>
                            <th className="p-4 font-bold border-b border-slate-200">X Coordinate</th>
                            <th className="p-4 font-bold border-b border-slate-200">Y Coordinate</th>
                            <th className="p-4 font-bold border-b border-slate-200">Width (ft)</th>
                            <th className="p-4 font-bold border-b border-slate-200">Length (ft)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {workflow.design?.rooms.map(r => (
                            <tr key={r.roomId} className="hover:bg-slate-50">
                              <td className="p-4 font-semibold text-slate-700">{r.name || formatRoomName(r.roomType)}</td>
                              <td className="p-4 font-mono text-slate-500">{r.x}</td>
                              <td className="p-4 font-mono text-slate-500">{r.y}</td>
                              <td className="p-4 font-mono text-slate-500">{r.width}</td>
                              <td className="p-4 font-mono text-slate-500">{r.length}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="h-[600px] bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
                      <div className="absolute top-4 left-4 z-10 flex gap-2">
                        {floorNumbers.length > 1 && floorNumbers.map(floor => (
                          <button
                            key={floor}
                            onClick={() => setSelectedFloor(floor)}
                            className={`px-4 py-1.5 rounded-lg text-sm font-bold shadow-sm ${selectedFloor === floor ? 'bg-slate-800 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'
                              }`}
                          >
                            {formatFloorName(floor)}
                          </button>
                        ))}
                      </div>
                      <FloorPlanViewer data={floorPlanData} pixelsPerFoot={24} floorFilter={selectedFloor} />
                    </div>
                  </div>
                </details>
              </section>
            )}

            {/* Section E: Planning / Feasibility Validation */}
            <section className="bg-white rounded-3xl p-4 md:p-6 md:p-8 shadow-sm border border-slate-200 h-fit">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <CheckCircle className="text-indigo-600" size={24} />
                Planning / Feasibility Validation
              </h2>
              {(() => {
                if (!workflow.validationResultJson) {
                  return (
                    <div className="text-sm text-slate-500 bg-slate-50 p-4 rounded-xl border border-slate-200">
                      Validation has not been completed yet.
                    </div>
                  );
                }

                let parsedValidation: any = null;
                try {
                  parsedValidation = JSON.parse(workflow.validationResultJson);
                } catch {
                  return <div className="text-sm text-red-500">Failed to parse validation data.</div>;
                }

                const finalValidationRules = (parsedValidation?.rules || []).filter(
                  (rule: any) => rule.ruleName?.toLowerCase() !== 'geometry'
                );
                const finalValidationPassed = parsedValidation?.passed ?? finalValidationRules.every(
                  (rule: any) => rule.status ? rule.status !== 'FAIL' : rule.passed
                );

                return (
                  <div className="space-y-4">
                    <div className={`p-4 rounded-xl border flex items-center justify-between ${
                      finalValidationPassed
                        ? 'bg-emerald-50 border-emerald-200'
                        : 'bg-red-50 border-red-200'
                    }`}>
                      <span className="font-semibold text-slate-800">Overall Result</span>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                        finalValidationPassed
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                          : 'bg-red-100 text-red-800 border-red-300'
                      }`}>
                        {finalValidationPassed ? 'PASS' : 'FAIL'}
                      </span>
                    </div>

                    {finalValidationRules.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-slate-800">Rule Breakdown</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {finalValidationRules.map((rule: any, idx: number) => (
                            <div key={idx} className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex flex-col gap-2 relative overflow-hidden">
                              <div className={`absolute top-0 left-0 w-1 h-full ${rule.status === 'NOT_APPLICABLE' ? 'bg-slate-400' : rule.passed ? 'bg-emerald-500' : 'bg-red-500'}`} />
                              <div className="flex items-start justify-between gap-2">
                                <span className="font-semibold text-sm text-slate-800 capitalize">
                                  {(rule.ruleName || '').replace(/_/g, ' ')}
                                </span>
                                <span className={`text-xs font-bold ${rule.status === 'NOT_APPLICABLE' ? 'text-slate-500' : rule.passed ? 'text-emerald-600' : 'text-red-600'}`}>
                                  {rule.status === 'NOT_APPLICABLE' ? 'NOT APPLICABLE' : rule.status || (rule.passed ? 'PASS' : 'FAIL')}
                                </span>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-xs mt-1">
                                <div>
                                  <span className="text-slate-500 block mb-0.5">Expected:</span>
                                  <span className="font-mono text-slate-800 break-words">{safeDisplayValue(rule.expected)}</span>
                                </div>
                                <div>
                                  <span className="text-slate-500 block mb-0.5">Actual:</span>
                                  <span className="font-mono text-slate-800 break-words">{safeDisplayValue(rule.actual)}</span>
                                </div>
                              </div>
                              {rule.reason && (
                                <div className="text-xs text-slate-500 mt-1 pt-2 border-t border-slate-200">
                                  {rule.reason}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </section>

            {/* Section F: Architect Review */}
            <section className="bg-white rounded-3xl p-4 md:p-6 md:p-8 shadow-sm border border-slate-200 h-fit">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-500">🧑‍💼</span>
                Architect Review
              </h2>

              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-semibold text-slate-700">Status:</span>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                    workflow.architectReviewStatus === 'Approved' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    workflow.architectReviewStatus === 'Rejected' ? 'bg-red-50 text-red-700 border-red-200' :
                    workflow.architectReviewStatus ? 'bg-amber-50 text-amber-700 border-amber-200' :
                    'bg-slate-50 text-slate-500 border-slate-200'
                  }`}>
                    {workflow.architectReviewStatus || 'Pending'}
                  </span>
                </div>

                {workflow.architectDecisionDate && (
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Clock size={16} />
                    <span>Decision Date: {new Date(workflow.architectDecisionDate).toLocaleString()}</span>
                  </div>
                )}

                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <span className="text-sm font-semibold text-slate-700 block mb-2">Comment:</span>
                  <p className="text-sm text-slate-600 whitespace-pre-wrap">
                    {workflow.architectFeedback || 'No architect comment provided.'}
                  </p>
                </div>
              </div>
            </section>

          </div>
        ) : (
          // Construction Plan View
          <div className="animate-fade-in bg-white rounded-3xl p-4 md:p-6 md:p-8 shadow-sm border border-slate-200">
            {!workflow.constructionPlan ? (
              <div className="text-center p-4 md:p-12 bg-slate-50 rounded-2xl border border-dashed border-slate-300">
                <p className="text-text-muted font-medium">No construction plan has been generated for this design yet.</p>
              </div>
            ) : (
              <div className="space-y-8">

                {/* Summary Header */}
                <div className="bg-slate-50 p-4 md:p-6 rounded-2xl border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h2 className="text-2xl font-bold text-slate-800">Project Timeline Estimate</h2>
                      {isAdmin && !isEditingPlan && (
                        <button onClick={startEditingPlan} className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
                          <Edit2 size={16} />
                        </button>
                      )}
                    </div>
                    <p className="text-slate-500 text-sm">AI-generated construction roadmap based on architectural design</p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl md:text-3xl font-black text-indigo-600">
                      {workflow.constructionPlan.project_summary.estimated_duration_days} <span className="text-lg text-slate-500 font-medium">days</span>
                    </div>
                    <div className="text-sm font-bold text-slate-400">
                      (~{workflow.constructionPlan.project_summary.estimated_duration_months} months)
                    </div>
                  </div>
                </div>

                {/* Target & Status */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <h4 className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-1">Target Duration</h4>
                    {isEditingPlan ? (
                      <input
                        type="number"
                        value={editTargetDuration}
                        onChange={e => setEditTargetDuration(e.target.value ? Number(e.target.value) : '')}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="e.g. 150"
                      />
                    ) : (
                      <p className="text-lg font-semibold text-slate-700">
                        {workflow.constructionPlan.project_summary.target_duration_days ? `${workflow.constructionPlan.project_summary.target_duration_days} days` : 'Not Provided'}
                      </p>
                    )}
                  </div>
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <h4 className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-1">Schedule Status</h4>
                    {isEditingPlan ? (
                      <select
                        value={editScheduleStatus}
                        onChange={e => setEditScheduleStatus(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="ON_SCHEDULE">ON SCHEDULE</option>
                        <option value="DELAYED">DELAYED</option>
                        <option value="AHEAD_OF_SCHEDULE">AHEAD OF SCHEDULE</option>
                      </select>
                    ) : (
                      <p className={`text-lg font-bold ${workflow.constructionPlan.project_summary.schedule_status === 'ON_SCHEDULE' ? 'text-emerald-600' :
                          workflow.constructionPlan.project_summary.schedule_status === 'DELAYED' ? 'text-red-600' : 'text-amber-600'
                        }`}>
                        {workflow.constructionPlan.project_summary.schedule_status.replace(/_/g, ' ')}
                      </p>
                    )}
                  </div>
                </div>

                {isEditingPlan && (
                  <div className="flex justify-end gap-3 mt-4">
                    <button onClick={() => setIsEditingPlan(false)} className="px-4 py-2 rounded-lg text-slate-600 font-semibold hover:bg-slate-100 text-sm">Cancel</button>
                    <button onClick={handleSavePlan} disabled={isSavingPlan} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2">
                      <Save size={16} /> {isSavingPlan ? 'Saving...' : 'Save Plan'}
                    </button>
                  </div>
                )}

                {/* Phases List */}
                <div>
                  <div className="flex items-center justify-between mb-4 mt-8">
                    <h3 className="text-xl font-bold text-slate-800">Construction Phases</h3>
                  </div>
                  <div className="space-y-3">
                    {workflow.constructionPlan.phases.map((phase: any) => (
                      <div key={phase.id} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between hover:border-indigo-300 transition-colors gap-4">
                        {editingPhaseId === phase.id ? (
                          // Edit Phase Form
                          <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-3">
                              <div><label className="text-xs font-bold text-slate-500 uppercase">Phase Name</label><input type="text" value={phaseFormData.name} onChange={e => setPhaseFormData({ ...phaseFormData, name: e.target.value })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" /></div>
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                                <div><label className="text-xs font-bold text-slate-500 uppercase">Duration</label><input type="number" value={phaseFormData.duration_days} onChange={e => setPhaseFormData({ ...phaseFormData, duration_days: Number(e.target.value) })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" /></div>
                                <div><label className="text-xs font-bold text-slate-500 uppercase">Start Day</label><input type="number" value={phaseFormData.start_day} onChange={e => setPhaseFormData({ ...phaseFormData, start_day: Number(e.target.value) })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" /></div>
                                <div><label className="text-xs font-bold text-slate-500 uppercase">End Day</label><input type="number" value={phaseFormData.end_day} onChange={e => setPhaseFormData({ ...phaseFormData, end_day: Number(e.target.value) })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" /></div>
                              </div>
                            </div>
                            <div className="flex items-end justify-end gap-2 pb-1">
                              <button onClick={cancelPhaseEdit} className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg"><X size={18} /></button>
                              <button onClick={savePhase} disabled={isSavingPlan} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold disabled:opacity-50 flex items-center gap-2"><Save size={16} /> Save</button>
                            </div>
                          </div>
                        ) : (
                          // View Phase
                          <>
                            <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 font-bold flex items-center justify-center shrink-0 border border-indigo-100">
                                {phase.id}
                              </div>
                              <div>
                                <h4 className="font-bold text-slate-800">{phase.name}</h4>
                                <p className="text-xs text-slate-500 mt-1 font-medium">
                                  {phase.depends_on.length > 0 ? `Depends on: ${phase.depends_on.join(', ')}` : 'No dependencies'}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-4 md:gap-6">
                              <div className="text-right">
                                <div className="font-bold text-slate-800">{phase.duration_days} days</div>
                                <div className="text-xs font-bold text-indigo-600 bg-indigo-50 border border-indigo-100 px-2 py-1 rounded-md mt-1 inline-block">
                                  Day {phase.start_day} – {phase.end_day}
                                </div>
                              </div>
                              {isAdmin && (
                                <div className="flex gap-1 border-l border-slate-100 pl-4">
                                  <button onClick={() => startEditingPhase(phase)} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"><Edit2 size={16} /></button>
                                  <button onClick={() => deletePhase(phase.id)} className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"><Trash2 size={16} /></button>
                                </div>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    ))}

                    {/* Add Phase Form */}
                    {isAddingPhase && (
                      <div className="bg-white p-4 rounded-xl border-2 border-indigo-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-3">
                            <div><label className="text-xs font-bold text-slate-500 uppercase">Phase Name</label><input type="text" value={phaseFormData.name} onChange={e => setPhaseFormData({ ...phaseFormData, name: e.target.value })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" placeholder="e.g. Foundation" /></div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                              <div><label className="text-xs font-bold text-slate-500 uppercase">Duration</label><input type="number" value={phaseFormData.duration_days} onChange={e => setPhaseFormData({ ...phaseFormData, duration_days: Number(e.target.value) })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" /></div>
                              <div><label className="text-xs font-bold text-slate-500 uppercase">Start Day</label><input type="number" value={phaseFormData.start_day} onChange={e => setPhaseFormData({ ...phaseFormData, start_day: Number(e.target.value) })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" /></div>
                              <div><label className="text-xs font-bold text-slate-500 uppercase">End Day</label><input type="number" value={phaseFormData.end_day} onChange={e => setPhaseFormData({ ...phaseFormData, end_day: Number(e.target.value) })} className="w-full border border-slate-200 bg-slate-50 rounded-lg px-3 py-2 text-sm mt-1" /></div>
                            </div>
                          </div>
                          <div className="flex items-end justify-end gap-2 pb-1">
                            <button onClick={cancelPhaseEdit} className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg"><X size={18} /></button>
                            <button onClick={savePhase} disabled={isSavingPlan} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold disabled:opacity-50 flex items-center gap-2"><Save size={16} /> Save</button>
                          </div>
                        </div>
                      </div>
                    )}

                    {isAdmin && !isAddingPhase && (
                      <button onClick={startAddingPhase} className="w-full py-4 border-2 border-dashed border-slate-300 rounded-xl text-slate-500 font-bold hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50/50 transition-colors flex items-center justify-center gap-2 mt-4">
                        <Plus size={20} /> Add New Phase
                      </button>
                    )}
                  </div>
                </div>

                {/* Critical Path & Notes */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mt-8">
                  <div className="bg-indigo-50 p-4 md:p-6 rounded-2xl border border-indigo-100">
                    <h4 className="font-bold text-indigo-900 mb-4">Critical Path</h4>
                    <ol className="list-decimal list-inside text-sm text-indigo-800 space-y-2 font-medium">
                      {workflow.constructionPlan.critical_path.map((cp: any) => <li key={cp}>{cp}</li>)}
                    </ol>
                  </div>

                  <div className="space-y-6">
                    {workflow.constructionPlan.optimization_notes.length > 0 && (
                      <div className="bg-amber-50 p-4 md:p-6 rounded-2xl border border-amber-100">
                        <h4 className="font-bold text-amber-900 mb-4">Optimization Notes</h4>
                        <ul className="list-disc list-inside text-sm text-amber-800 space-y-2 font-medium">
                          {workflow.constructionPlan.optimization_notes.map((note: any) => <li key={note}>{note}</li>)}
                        </ul>
                      </div>
                    )}

                    <div className="bg-slate-50 p-4 md:p-6 rounded-2xl border border-slate-200">
                      <h4 className="font-bold text-slate-700 mb-4">AI Assumptions</h4>
                      <ul className="list-disc list-inside text-sm text-slate-600 space-y-2 font-medium">
                        {workflow.constructionPlan.assumptions.map((assumption: any) => <li key={assumption}>{assumption}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
