import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { workflowService, type WorkflowStatusResponseDto } from '../services/workflowService';
import { FloorPlanViewer, type FloorPlanData } from '../components/floorplan/FloorPlanViewer';
import { Menu } from 'lucide-react';

export const WorkflowReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<WorkflowStatusResponseDto | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<number>(1);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);

  useEffect(() => {
    if (!id) return;

    let interval: ReturnType<typeof setInterval>;

    const fetchWorkflow = async () => {
      try {
        const data = await workflowService.getWorkflowStatus(id);
        setWorkflow(data);
        setError(null);
        setLoading(false);

        // If the status is no longer running, we can stop polling
        if (data.status !== 'running' && data.status !== 'pending') {
          clearInterval(interval);
        }
      } catch (err: any) {
        // If it's a 404, the workflow is likely still being created by the background task
        if (err.response?.status === 404 || err.message?.includes('404')) {
          // Keep loading, don't set error
          setError(null);
        } else {
          setError(err.message || 'Failed to fetch workflow status');
          setLoading(false);
          clearInterval(interval);
        }
      }
    };

    // Initial fetch
    fetchWorkflow();

    // Poll every 3 seconds until workflow is ready
    interval = setInterval(() => {
      fetchWorkflow();
    }, 3000);

    return () => clearInterval(interval);
  }, [id]);

  // ─── Loading State ───
  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-65px)] bg-gradient-to-br from-slate-50 to-zinc-100">
        <div className="text-center p-8 bg-white/60 backdrop-blur-md rounded-2xl shadow-sm border border-white">
          <div className="relative inline-block mb-4">
            <div className="w-12 h-12 border-4 border-indigo-200 rounded-full"></div>
            <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin absolute top-0 left-0"></div>
          </div>
          <p className="text-zinc-600 font-medium tracking-wide">Loading design environment...</p>
        </div>
      </div>
    );
  }

  // ─── Error State ───
  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-65px)] bg-gradient-to-br from-red-50 to-red-100/50">
        <div className="bg-white/80 backdrop-blur-xl p-10 rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-red-100 max-w-md text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner">
            <div className="text-red-500 text-3xl font-bold">!</div>
          </div>
          <h2 className="text-2xl font-bold text-zinc-900 mb-3 tracking-tight">Error Loading Design</h2>
          <p className="text-red-600 text-sm font-medium bg-red-50 p-4 rounded-xl">{error}</p>
        </div>
      </div>
    );
  }

  // ─── Design Not Ready ───
  if (!workflow || !workflow.design) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-65px)] bg-gradient-to-br from-slate-50 to-zinc-100 relative overflow-hidden">
        <div className="absolute top-1/4 right-1/3 w-64 h-64 bg-indigo-200/40 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob"></div>
        <div className="bg-white/90 backdrop-blur-xl p-12 rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white/60 max-w-md text-center relative z-10">
          <div className="w-20 h-20 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-inner border border-indigo-100/50">
            <span className="text-4xl">🏗️</span>
          </div>
          <h2 className="text-2xl font-bold text-zinc-900 mb-3 tracking-tight">Design In Progress</h2>
          <p className="text-zinc-500 text-sm leading-relaxed mb-6 font-medium">
            The AI Architect is actively computing geometries and generating your house layout. This page will update automatically.
          </p>
          <div className="inline-flex items-center gap-2 bg-zinc-100/80 px-4 py-2 rounded-full border border-zinc-200/50">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
            </span>
            <p className="text-xs text-zinc-600 font-bold uppercase tracking-wider">{workflow?.status?.replace(/_/g, ' ') || 'initializing'}</p>
          </div>
        </div>
      </div>
    );
  }

  // ─── Map API DTO to FloorPlanViewer props ───
  const floorPlanData: FloorPlanData = {
    design_id: workflow.design.designId,
    floor_count: workflow.design.floorCount,
    total_built_up_area_sqft: workflow.design.totalBuiltUpAreaSqft,
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

  const handleAction = async (decision: 'approve' | 'reject' | 'request_revision') => {
    if (!id) return;
    try {
      await workflowService.approveWorkflow(id, decision, decision === 'reject' ? 'Architect rejected' : '');
      alert(`Workflow ${decision} submitted successfully!`);
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    }
  };

  // Count rooms by type for summary
  const bedroomCount = workflow.design.rooms.filter(r => r.roomType.includes('bedroom')).length;
  const bathroomCount = workflow.design.rooms.filter(r => r.roomType.includes('bathroom')).length;

  return (
    <div className="flex h-screen bg-slate-50">
      {/* ─── Sidebar: Details ─── */}
      {isSidebarOpen && (
        <div className="w-80 bg-white/90 backdrop-blur-xl border-r border-zinc-200/60 flex flex-col shadow-[4px_0_24px_-12px_rgba(0,0,0,0.1)] overflow-y-auto shrink-0 transition-all duration-300 z-10">
          {/* Header */}
          <div className="p-6 border-b border-zinc-100 flex justify-between items-center bg-gradient-to-b from-zinc-50/50 to-transparent">
            <div>
              <h1 className="text-xl font-bold text-zinc-900 tracking-tight">Design Review</h1>
              <p className="text-[11px] font-medium text-zinc-400 mt-1 uppercase tracking-wider">ID: {id?.slice(0, 8)}...</p>
            </div>
          </div>

        <div className="p-6 space-y-5 flex-1">
          {/* Status */}
          <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-100 shadow-sm">
            <h3 className="text-[10px] uppercase tracking-widest text-zinc-400 font-bold mb-3">Status</h3>
            <span className={`px-3 py-1.5 rounded-lg text-xs font-bold tracking-wide shadow-sm ${workflow.status === 'awaiting_approval' ? 'bg-amber-100 text-amber-800 border border-amber-200' : 'bg-indigo-100 text-indigo-800 border border-indigo-200'}`}>
              {workflow.status.replace(/_/g, ' ').toUpperCase()}
            </span>
          </div>

          {/* Design Version */}
          <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-100 shadow-sm">
            <h3 className="text-[10px] uppercase tracking-widest text-zinc-400 font-bold mb-3">Design Info</h3>
            <ul className="text-sm text-zinc-700 space-y-2">
              <li className="flex justify-between items-center"><span className="font-medium text-zinc-500">Version</span> <span className="font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">v{workflow.design.version}</span></li>
              <li className="flex justify-between items-center"><span className="font-medium text-zinc-500">Template</span> <span className="font-bold">{workflow.design.templateId || 'N/A'}</span></li>
            </ul>
          </div>

          {/* Specifications */}
          <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-100 shadow-sm">
            <h3 className="text-[10px] uppercase tracking-widest text-zinc-400 font-bold mb-3">Specifications</h3>
            <ul className="text-sm text-zinc-700 space-y-2">
              <li className="flex justify-between items-center"><span className="font-medium text-zinc-500">Terrain</span> <span className="font-bold capitalize">{workflow.terrainType || 'N/A'}</span></li>
              {workflow.slopeEstimate && (
                <li className="flex justify-between items-center"><span className="font-medium text-zinc-500">Slope</span> <span className="font-bold capitalize">{workflow.slopeEstimate}</span></li>
              )}
              <li className="flex justify-between items-center"><span className="font-medium text-zinc-500">Foundation</span> <span className="font-bold capitalize">{workflow.design.foundationType}</span></li>
              <li className="flex justify-between items-center"><span className="font-medium text-zinc-500">Floors</span> <span className="font-bold">{workflow.design.floorCount}</span></li>
              <li className="flex justify-between items-center"><span className="font-medium text-zinc-500">Area</span> <span className="font-bold">{workflow.design.totalBuiltUpAreaSqft} sqft</span></li>
            </ul>
          </div>

          {/* Room Summary */}
          <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-100 shadow-sm">
            <h3 className="text-[10px] uppercase tracking-widest text-zinc-400 font-bold mb-3 flex items-center justify-between">
              Rooms <span className="bg-zinc-200 text-zinc-600 px-1.5 py-0.5 rounded">{workflow.design.rooms.length}</span>
            </h3>
            <div className="flex gap-2 mb-4">
              <span className="text-[11px] bg-indigo-100/80 border border-indigo-200 text-indigo-700 px-2 py-1 rounded-md font-bold shadow-sm">{bedroomCount} Bed</span>
              <span className="text-[11px] bg-emerald-100/80 border border-emerald-200 text-emerald-700 px-2 py-1 rounded-md font-bold shadow-sm">{bathroomCount} Bath</span>
            </div>
            <ul className="text-sm text-zinc-600 max-h-48 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
              {workflow.design.rooms.map(r => (
                <li key={r.roomId} className="flex justify-between items-center text-xs p-2 bg-white rounded-lg border border-zinc-100 shadow-sm">
                  <span className="font-semibold text-zinc-700">{r.name || r.roomType.replace(/_/g, ' ')}</span>
                  <span className="text-[10px] font-bold text-zinc-400">{r.width}'×{r.length}' (F{r.floorNumber})</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="p-6 border-t border-zinc-200 flex flex-col gap-3 bg-white">
          <button
            onClick={() => handleAction('approve')}
            className="w-full py-3 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-xl font-bold hover:from-emerald-600 hover:to-emerald-700 transition-all text-sm shadow-[0_4px_14px_0_rgb(16,185,129,0.39)] hover:shadow-[0_6px_20px_rgba(16,185,129,0.23)]"
          >
            ✓ Approve Design
          </button>
          <button
            onClick={() => handleAction('request_revision')}
            className="w-full py-3 bg-white text-indigo-600 border-2 border-indigo-100 rounded-xl font-bold hover:bg-indigo-50 hover:border-indigo-200 transition-all text-sm"
          >
            ↻ Request Revision
          </button>
          <button
            onClick={() => handleAction('reject')}
            className="w-full py-3 bg-white text-red-500 border-2 border-red-100 rounded-xl font-bold hover:bg-red-50 hover:border-red-200 transition-all text-sm mt-2"
          >
            ✕ Reject
          </button>
        </div>
      </div>
      )}

      {/* ─── Main Area: Floor Plan ─── */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top Action Bar */}
        <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-4">
          <button 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 text-slate-500 hover:bg-slate-100 rounded-md transition-colors"
            title="Toggle Sidebar"
          >
            <Menu size={20} />
          </button>
          
          {/* Floor Tabs */}
          {floorNumbers.length > 1 && (
            <div className="flex gap-2">
              {floorNumbers.map(floor => (
                <button
                  key={floor}
                  onClick={() => setSelectedFloor(floor)}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedFloor === floor
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Floor {floor}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* SVG Floor Plan */}
        <div className="flex-1 overflow-auto relative">
          <FloorPlanViewer
            data={floorPlanData}
            pixelsPerFoot={22}
            floorFilter={selectedFloor}
          />
        </div>
      </div>
    </div>
  );
};
