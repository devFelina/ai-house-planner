import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { workflowService, type WorkflowStatusResponseDto } from '../services/workflowService';
import { FloorPlanViewer, type FloorPlanData } from '../components/floorplan/FloorPlanViewer';

export const WorkflowReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<WorkflowStatusResponseDto | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<number>(1);

  useEffect(() => {
    if (!id) return;

    const fetchWorkflow = async () => {
      try {
        const data = await workflowService.getWorkflowStatus(id);
        setWorkflow(data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch workflow status');
      } finally {
        setLoading(false);
      }
    };

    fetchWorkflow();

    // Poll if status is 'running' or 'design_generated' (waiting for cost/validation)
    const interval = setInterval(() => {
      if (workflow?.status === 'running') {
        fetchWorkflow();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [id, workflow?.status]);

  // ─── Loading State ───
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-slate-500 text-sm">Loading design...</p>
        </div>
      </div>
    );
  }

  // ─── Error State ───
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="bg-white p-8 rounded-xl shadow-sm border border-red-100 max-w-md text-center">
          <div className="text-red-500 text-4xl mb-4">⚠</div>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Error Loading Design</h2>
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // ─── Design Not Ready ───
  if (!workflow || !workflow.design) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-100 max-w-md text-center">
          <div className="text-4xl mb-4">🏗️</div>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Design In Progress</h2>
          <p className="text-slate-500 text-sm">The AI is currently generating your house design. This page will update automatically.</p>
          <p className="text-xs text-slate-400 mt-4">Workflow status: {workflow?.status || 'unknown'}</p>
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
      <div className="w-80 bg-white border-r border-slate-200 flex flex-col shadow-sm overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-slate-100">
          <h1 className="text-xl font-bold text-slate-800">Design Review</h1>
          <p className="text-xs text-slate-400 mt-1">Workflow {id?.slice(0, 8)}...</p>
        </div>

        <div className="p-6 space-y-4 flex-1">
          {/* Status */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Status</h3>
            <span className={`px-2 py-1 rounded text-xs font-medium ${workflow.status === 'awaiting_approval' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'}`}>
              {workflow.status.replace(/_/g, ' ').toUpperCase()}
            </span>
          </div>

          {/* Design Version */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Design Info</h3>
            <ul className="text-sm text-slate-700 space-y-1.5">
              <li className="flex justify-between"><span>Version:</span> <span className="font-semibold text-indigo-600">v{workflow.design.version}</span></li>
              <li className="flex justify-between"><span>Template:</span> <span className="font-medium">{workflow.design.templateId || 'N/A'}</span></li>
            </ul>
          </div>

          {/* Specifications */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Specifications</h3>
            <ul className="text-sm text-slate-700 space-y-1.5">
              <li className="flex justify-between"><span>Terrain:</span> <span className="font-medium capitalize">{workflow.terrainType || 'N/A'}</span></li>
              {workflow.slopeEstimate && (
                <li className="flex justify-between"><span>Slope:</span> <span className="font-medium capitalize">{workflow.slopeEstimate}</span></li>
              )}
              <li className="flex justify-between"><span>Foundation:</span> <span className="font-medium capitalize">{workflow.design.foundationType}</span></li>
              <li className="flex justify-between"><span>Floors:</span> <span className="font-medium">{workflow.design.floorCount}</span></li>
              <li className="flex justify-between"><span>Total Area:</span> <span className="font-medium">{workflow.design.totalBuiltUpAreaSqft} sqft</span></li>
            </ul>
          </div>

          {/* Room Summary */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">
              Rooms ({workflow.design.rooms.length})
            </h3>
            <div className="flex gap-3 mb-3">
              <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded font-medium">{bedroomCount} Bed</span>
              <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-1 rounded font-medium">{bathroomCount} Bath</span>
            </div>
            <ul className="text-sm text-slate-600 max-h-40 overflow-y-auto space-y-1">
              {workflow.design.rooms.map(r => (
                <li key={r.roomId} className="flex justify-between text-xs">
                  <span>{r.name || r.roomType.replace(/_/g, ' ')}</span>
                  <span className="text-slate-400">{r.width}'×{r.length}' (F{r.floorNumber})</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="p-6 border-t border-slate-200 flex flex-col gap-3">
          <button
            onClick={() => handleAction('approve')}
            className="w-full py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors text-sm"
          >
            ✓ Approve Design
          </button>
          <button
            onClick={() => handleAction('request_revision')}
            className="w-full py-2.5 bg-white text-indigo-600 border border-indigo-200 rounded-lg font-medium hover:bg-indigo-50 transition-colors text-sm"
          >
            ↻ Request Revision
          </button>
          <button
            onClick={() => handleAction('reject')}
            className="w-full py-2 bg-white text-red-500 border border-red-200 rounded-lg font-medium hover:bg-red-50 transition-colors text-sm"
          >
            ✕ Reject
          </button>
        </div>
      </div>

      {/* ─── Main Area: Floor Plan ─── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Floor Tabs */}
        {floorNumbers.length > 1 && (
          <div className="bg-white border-b border-slate-200 px-6 py-3 flex gap-2">
            {floorNumbers.map(floor => (
              <button
                key={floor}
                onClick={() => setSelectedFloor(floor)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
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
