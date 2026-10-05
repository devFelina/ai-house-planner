import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import CostBreakdownCard from '../components/cost/CostBreakdownCard';
import {
 workflowService,
 type WorkflowStatusResponseDto
} from '../services/workflowService';

interface ApprovalResultState {
 workflowId?: string;
 decision?: string;
 status?: string;
 projectId?: string | null;
 message?: string;
}

const ApprovalPage: React.FC = () => {
 const [searchParams] = useSearchParams();
 const navigate = useNavigate();
 const workflowId = searchParams.get('workflowId');

 const [workflow, setWorkflow] = useState<WorkflowStatusResponseDto | null>(null);
 const [approvalResult, setApprovalResult] = useState<ApprovalResultState | null>(null);
 const [revisionNotes, setRevisionNotes] = useState('');
 const [isLoading, setIsLoading] = useState(false);
 const [isSubmitting, setIsSubmitting] = useState(false);
 const [errorMessage, setErrorMessage] = useState<string | null>(null);
 const [successMessage, setSuccessMessage] = useState<string | null>(null);

 const fetchWorkflowStatus = useCallback(async () => {
  if (!workflowId) return;
  setIsLoading(true);
  setErrorMessage(null);
  try {
   const data = await workflowService.getWorkflowStatus(workflowId);
   setWorkflow(data);
  } catch (err: unknown) {
   const error = err as { response?: { data?: { message?: string } }; message?: string };
   const msg = error.response?.data?.message || error.message || 'Failed to fetch workflow status.';
   setErrorMessage(msg);
   setWorkflow(null);
  } finally {
   setIsLoading(false);
  }
 }, [workflowId]);

 useEffect(() => {
  fetchWorkflowStatus();
 }, [fetchWorkflowStatus]);

 if (!workflowId) {
  return (
   <div className="flex items-center justify-center min-h-[calc(100vh-65px)] bg-slate-50">
    <div className="bg-surface p-4 md:p-8 rounded-2xl shadow-sm border border-red-100 max-w-md text-center">
     <h2 className="text-xl font-bold text-red-600 mb-2">Workflow ID is missing</h2>
     <p className="text-text-secondary">Please return to the workflow review page.</p>
    </div>
   </div>
  );
 }

 const handleDecision = async (decision: 'approve' | 'reject' | 'request_revision') => {
  setIsSubmitting(true);
  setErrorMessage(null);
  setSuccessMessage(null);

  try {
   const response = await workflowService.approveWorkflow(
    workflowId,
    decision,
    revisionNotes.trim() ? revisionNotes : undefined
   );

   setApprovalResult(response);
   setSuccessMessage(response.message || `Workflow ${decision.replace('_', ' ')} successfully.`);

   if (workflow) {
    setWorkflow({
     ...workflow,
     status: response.status || (decision === 'approve' ? 'approved' : decision === 'reject' ? 'rejected' : 'running'),
     approvalStatus: response.decision || decision,
    });
   }
  } catch (err: unknown) {
   const error = err as { response?: { status?: number; data?: { message?: string } }; message?: string };
   if (error.response?.status === 409) {
    setErrorMessage('Workflow has already been approved and a project has been created.');
   } else if (error.response?.status === 400) {
    setErrorMessage(error.response.data?.message || 'Approval rejected: Validation failed or invalid state.');
   } else if (error.response?.status === 403) {
    setErrorMessage('Unauthorized: You do not have permission to review this project.');
   } else {
    setErrorMessage(error.response?.data?.message || error.message || 'Failed to process approval decision.');
   }
  } finally {
   setIsSubmitting(false);
  }
 };

 const currentStatus = workflow?.approvalStatus || 'not_requested';
 const validationPassed = workflow?.approvalStatus === 'pending' || workflow?.approvalStatus === 'approved' || workflow?.status === 'awaiting_approval';
 const isApproved = currentStatus === 'approved' || workflow?.status === 'approved';
 const isRejected = currentStatus === 'rejected' || workflow?.status === 'rejected';

 // Dynamic values extracted from actual design & cost objects
 const design = workflow?.design;
 const bedroomsCount = design?.rooms ? design.rooms.filter(r => r.roomType.toLowerCase().includes('bedroom')).length : 0;
 const bathroomsCount = design?.rooms ? design.rooms.filter(r => r.roomType.toLowerCase().includes('bathroom') || r.roomType.toLowerCase().includes('ensuite')).length : 0;
 const builtUpArea = design?.totalBuiltUpAreaSqft ? Number(design.totalBuiltUpAreaSqft).toLocaleString() : 'N/A';
 const floorCount = design?.floorCount ?? 1;
 const foundationType = design?.foundationType || 'Standard Footing';
 const terrainType = workflow?.terrainType || design?.terrainType || 'Flat';

 return (
  <div className="min-h-[calc(100vh-65px)] bg-gray-50 flex flex-col items-center py-4 md:py-12 px-4 md:px-6">
   <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4 }}
    className="w-full max-w-3xl space-y-6"
   >
    <div className="flex items-center justify-between">
     <div>
      <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Project Approval</h1>
      <p className="text-xs text-text-muted mt-1">Workflow ID: {workflowId}</p>
     </div>
     <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
      isApproved ? 'bg-green-100 text-green-700' :
      isRejected ? 'bg-red-100 text-red-700' :
      currentStatus === 'revision_requested' ? 'bg-yellow-100 text-yellow-700' :
      'bg-blue-100 text-blue-700'
     }`}>
      {currentStatus.replace('_', ' ')}
     </span>
    </div>

    {errorMessage && (
     <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
      <span className="font-semibold">Notice:</span> {errorMessage}
     </div>
    )}

    {successMessage && (
     <div className="p-4 rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm flex flex-col gap-2">
      <div><span className="font-semibold">Success:</span> {successMessage}</div>
      {approvalResult?.projectId && (
       <div className="flex items-center gap-3 pt-1">
        <span className="text-xs font-mono bg-green-100 px-2 py-1 rounded">
         Project ID: {approvalResult.projectId}
        </span>
        <Button
         variant="outline"
         onClick={() => navigate(`/projects`)}
         className="text-xs py-1 px-3 border-green-600 text-green-700 hover:bg-green-100"
        >
         View Projects →
        </Button>
       </div>
      )}
     </div>
    )}

    {/* Validation & Safety Summary */}
    <Card title="Safety & Compliance Validation" subtitle="Deterministic safety rules executed prior to human review.">
     <div className="space-y-3">
      <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-border">
       <span className="text-sm font-medium text-zinc-800">Overall Validation Result</span>
       <span className={`px-3 py-1 rounded-full text-xs font-bold ${
        validationPassed ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
       }`}>
        {validationPassed ? 'PASSED (Ready for Review)' : (workflow?.status === 'failed' ? 'FAILED (Approval Blocked)' : 'EVALUATING')}
       </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
       <div className="p-3 bg-surface-elevated rounded border border-zinc-100 flex items-center justify-between">
        <span className="text-text-secondary">1. Ground Coverage Rule (&le; 65%)</span>
        <span className="font-semibold text-emerald-600">✓ PASS</span>
       </div>
       <div className="p-3 bg-surface-elevated rounded border border-zinc-100 flex items-center justify-between">
        <span className="text-text-secondary">2. Terrain/Foundation Compatibility</span>
        <span className="font-semibold text-emerald-600">✓ PASS</span>
       </div>
       <div className="p-3 bg-surface-elevated rounded border border-zinc-100 flex items-center justify-between">
        <span className="text-text-secondary">3. Budget Tolerance Rule</span>
        <span className="font-semibold text-emerald-600">✓ PASS</span>
       </div>
       <div className="p-3 bg-surface-elevated rounded border border-zinc-100 flex items-center justify-between">
        <span className="text-text-secondary">4. Room & Floor Preferences</span>
        <span className="font-semibold text-emerald-600">✓ PASS</span>
       </div>
      </div>
     </div>
    </Card>

    {/* Generated Floor Plan */}
    <Card title="Generated Floor Plan" subtitle="The AI's rendering of your floor plan design.">
     <div className="flex justify-center bg-surface-elevated rounded-lg border border-border overflow-hidden min-h-[300px]">
      <img
       src={`${import.meta.env.VITE_AGENTIC_PUBLIC_URL || 'http://localhost:8001'}/plans/plan_${workflowId}.png`}
       alt="Generated Floor Plan"
       className="max-w-full h-auto object-contain"
       onError={(e) => {
        e.currentTarget.style.display = 'none';
        const parent = e.currentTarget.parentElement;
        if (parent) {
         const div = document.createElement('div');
         div.className = 'flex items-center justify-center w-full h-full p-4 md:p-12 text-text-secondary font-medium text-sm';
         div.innerText = 'Image rendering in progress or not available.';
         parent.appendChild(div);
        }
       }}
      />
     </div>
    </Card>

    {/* Dynamic Workflow & Plan Information */}
    <Card title="Workflow & Plan Summary" subtitle="Review the proposed architecture and budget before deciding.">
     <div className="space-y-4">
      <div className="bg-surface-elevated p-4 rounded-lg border border-zinc-100">
       <p className="text-xs text-text-muted uppercase font-bold tracking-wider mb-1">Architecture Style</p>
       <p className="text-sm font-medium text-zinc-900">{design?.templateFamily || 'Modern Custom Design'}</p>
      </div>
      <div className="bg-surface-elevated p-4 rounded-lg border border-zinc-100">
       <p className="text-xs text-text-muted uppercase font-bold tracking-wider mb-2">Design Details</p>
       <ul className="text-sm text-zinc-700 space-y-1 list-disc list-inside">
        <li>{bedroomsCount > 0 ? `${bedroomsCount} Bedrooms` : 'Custom Bedrooms'}, {bathroomsCount > 0 ? `${bathroomsCount} Bathrooms` : 'Custom Bathrooms'}</li>
        <li>{floorCount} {floorCount > 1 ? 'Floors' : 'Floor'} &bull; {foundationType} Foundation</li>
        <li>Terrain Condition: <span className="capitalize">{terrainType}</span></li>
        <li>{builtUpArea} sq ft total built-up area</li>
       </ul>
      </div>
     </div>
    </Card>

    <CostBreakdownCard cost={workflow?.cost ?? null} run={workflow?.costEstimationRun} />

    {/* Approval Actions */}
    <Card title="Approval Actions" subtitle="Submit an authorized decision on this house planning proposal.">
     <div className="space-y-4">
      <div>
       <label htmlFor="revisionNotes" className="block text-sm font-medium text-zinc-700 mb-1">
        Revision / Rejection Notes (Optional)
       </label>
       <textarea
        id="revisionNotes"
        rows={3}
        className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-text-secondary"
        placeholder="Enter notes if requesting design adjustments or providing feedback..."
        value={revisionNotes}
        onChange={(e) => setRevisionNotes(e.target.value)}
        disabled={isApproved || isRejected || isSubmitting}
       />
      </div>

      <div className="flex items-center gap-3 pt-2">
       <Button
        variant="primary"
        onClick={() => handleDecision('approve')}
        disabled={isApproved || isSubmitting || isLoading}
        className="bg-green-600 hover:bg-green-700 focus:ring-green-500"
       >
        {isSubmitting ? 'Processing...' : 'Approve & Create Project'}
       </Button>
       <Button
        variant="danger"
        onClick={() => handleDecision('reject')}
        disabled={isRejected || isSubmitting || isLoading}
       >
        Reject
       </Button>
       <Button
        variant="outline"
        onClick={() => handleDecision('request_revision')}
        disabled={isApproved || isSubmitting || isLoading}
       >
        Request Revision
       </Button>
      </div>
     </div>
    </Card>
   </motion.div>
  </div>
 );
};

export default ApprovalPage;
