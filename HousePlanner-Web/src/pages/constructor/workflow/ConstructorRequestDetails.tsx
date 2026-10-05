import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { constructorWorkflowService } from '../../../services/constructorWorkflowService';
import CostBreakdownCard from '../../../components/cost/CostBreakdownCard';
import { ArrowLeft, Check, X } from 'lucide-react';

export const ConstructorRequestDetails: React.FC = () => {
 const { requestId } = useParams<{ requestId: string }>();
 const navigate = useNavigate();
 const [request, setRequest] = useState<any>(null);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState('');
 const [actionLoading, setActionLoading] = useState(false);

 useEffect(() => {
  const fetchRequest = async () => {
   try {
    if (!requestId) return;
    const data = await constructorWorkflowService.getConstructorRequest(requestId);
    setRequest(data);
   } catch (err) {
    setError('Failed to load request details.');
   } finally {
    setLoading(false);
   }
  };
  void fetchRequest();
 }, [requestId]);

 const handleAccept = async () => {
  if (!requestId) return;
  setActionLoading(true);
  try {
   await constructorWorkflowService.acceptRequest(requestId);
   navigate('/constructor/dashboard');
  } catch (e: any) {
   alert(e.response?.data?.message || 'Could not accept request.');
  } finally {
   setActionLoading(false);
  }
 };

 const handleDecline = async () => {
  if (!requestId) return;
  const reason = window.prompt('Optional reason for declining') || undefined;
  setActionLoading(true);
  try {
   await constructorWorkflowService.declineRequest(requestId, reason);
   navigate('/constructor/dashboard');
  } catch (e: any) {
   alert(e.response?.data?.message || 'Could not decline request.');
  } finally {
   setActionLoading(false);
  }
 };

 if (loading) {
  return (
   <div className="flex h-64 items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
   </div>
  );
 }

 if (error || !request) {
  return (
   <div className="mx-auto max-w-7xl px-4 py-4 md:py-8 sm:px-6 lg:px-8">
    <p className="text-red-500">{error || 'Request not found'}</p>
    <Link to="/constructor/dashboard" className="text-indigo-600 hover:underline">Back to Dashboard</Link>
   </div>
  );
 }

 return (
  <div className="mx-auto max-w-7xl px-4 py-4 md:py-8 sm:px-6 lg:px-8">
   <Link to="/constructor/dashboard" className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-gray-900 dark:hover:text-text-primary mb-6">
    <ArrowLeft size={16} /> Back to Dashboard
   </Link>

   <div className="flex flex-col lg:flex-row gap-4 md:gap-8">
    {/* Left Column: Design Visualization */}
    <div className="flex-1 space-y-6">
     <div className="rounded-2xl border bg-surface p-4 md:p-6 bg-surface dark:border-border-strong">
      <h2 className="text-xl font-bold text-gray-900 dark:text-text-primary mb-4">Design Visualization</h2>
      <div className="aspect-square w-full rounded-xl border border-gray-100 bg-gray-50/50 dark:border-border-strong bg-surface/50 overflow-hidden">
       {request.aiVisualizationUrl ? (
        <img src={request.aiVisualizationUrl} alt="Approved design visualization" className="w-full h-full object-contain" />
       ) : (
        <div className="flex h-full items-center justify-center text-text-muted text-center p-4">
         Visualization image is not available for this design.
        </div>
       )}
      </div>
     </div>
    </div>

    {/* Right Column: Details & Actions */}
    <div className="w-full lg:w-[400px] space-y-6">
     <div className="rounded-2xl border bg-surface p-4 md:p-6 bg-surface dark:border-border-strong">
      <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-1">New Construction Request</p>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-text-primary">{request.title}</h1>
      <p className="text-sm text-text-secondary mt-2">Customer: <strong className="text-gray-900 dark:text-text-primary">{request.customerName}</strong></p>
      <p className="text-sm text-text-secondary mt-1">Requested: {new Date(request.requestedAt).toLocaleDateString()}</p>
      
      <div className="mt-6 border-t pt-6 dark:border-border-strong">
       <h3 className="text-sm font-semibold mb-3 dark:text-text-primary">Design Information</h3>
       <dl className="space-y-2 text-sm">
        <div className="flex justify-between">
         <dt className="text-text-secondary">Bedrooms</dt>
         <dd className="font-medium dark:text-text-primary">{request.bedrooms}</dd>
        </div>
        <div className="flex justify-between">
         <dt className="text-text-secondary">Bathrooms</dt>
         <dd className="font-medium dark:text-text-primary">{request.bathrooms}</dd>
        </div>
        <div className="flex justify-between">
         <dt className="text-text-secondary">Floors</dt>
         <dd className="font-medium dark:text-text-primary">{request.floorCount}</dd>
        </div>
        <div className="flex justify-between">
         <dt className="text-text-secondary">Built-up Area</dt>
         <dd className="font-medium dark:text-text-primary">{Number(request.area).toLocaleString()} sq ft</dd>
        </div>
        {request.terrainType && (
         <div className="flex justify-between">
          <dt className="text-text-secondary">Terrain / Site</dt>
          <dd className="font-medium dark:text-text-primary capitalize">{request.terrainType}</dd>
         </div>
        )}
        {request.planReference && (
         <div className="flex justify-between">
          <dt className="text-text-secondary">Plan Reference</dt>
          <dd className="font-medium dark:text-text-primary">{request.planReference}</dd>
         </div>
        )}
        {request.layoutType && (
         <div className="flex justify-between">
          <dt className="text-text-secondary">Layout Type</dt>
          <dd className="font-medium dark:text-text-primary">{request.layoutType}</dd>
         </div>
        )}
       </dl>
      </div>
      
      <div className="mt-6 border-t pt-6 dark:border-border-strong">
       <h3 className="text-sm font-semibold mb-3 dark:text-text-primary">Estimated Cost</h3>
       {request.cost ? (
        <CostBreakdownCard cost={request.cost} hideTitle />
       ) : (
        <p className="text-sm text-text-muted">Cost estimate is not available yet.</p>
       )}
      </div>

      {request.status === 'Pending' && (
       <div className="mt-8 flex gap-3">
        <button
         onClick={handleDecline}
         disabled={actionLoading}
         className="flex-1 flex items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
        >
         <X size={16} /> Decline
        </button>
        <button
         onClick={handleAccept}
         disabled={actionLoading}
         className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-text-primary text-sm font-semibold hover:bg-emerald-500 disabled:opacity-50"
        >
         <Check size={16} /> Accept Request
        </button>
       </div>
      )}
     </div>
    </div>
   </div>
  </div>
 );
};
export default ConstructorRequestDetails;
