import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Button from '../components/common/Button';
import Card from '../components/common/Card';

type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'revision_requested';

const ApprovalPage: React.FC = () => {
  const [status, setStatus] = useState<ApprovalStatus>('pending');
  const [revisionNotes, setRevisionNotes] = useState('');

  // TODO: Connect to actual backend API later (e.g., POST /api/v1/workflows/{id}/approve)
  const handleDecision = (decision: ApprovalStatus) => {
    setStatus(decision);
    if (decision !== 'revision_requested') {
      setRevisionNotes('');
    }
  };

  return (
    <div className="min-h-[calc(100vh-65px)] bg-gray-50 flex flex-col items-center py-12 px-6">
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-3xl space-y-6"
      >
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Project Approval</h1>
          <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
            status === 'approved' ? 'bg-green-100 text-green-700' :
            status === 'rejected' ? 'bg-red-100 text-red-700' :
            status === 'revision_requested' ? 'bg-yellow-100 text-yellow-700' :
            'bg-blue-100 text-blue-700'
          }`}>
            {status.replace('_', ' ')}
          </span>
        </div>

        <Card title="Workflow & Plan Information" subtitle="Review the current project details before making a decision.">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-100">
                <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-1">Project Name</p>
                <p className="text-sm font-medium text-zinc-900">Modern Minimalist Villa</p>
              </div>
              <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-100">
                <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-1">Estimated Cost</p>
                <p className="text-sm font-medium text-zinc-900">LKR 12,500,000</p>
              </div>
            </div>
            <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-100">
              <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-2">Design Details</p>
              <ul className="text-sm text-zinc-700 space-y-1 list-disc list-inside">
                <li>4 Bedrooms, 3 Bathrooms</li>
                <li>Open concept living and dining area</li>
                <li>Outdoor patio with pool</li>
                <li>2,450 sq ft total floor area</li>
              </ul>
            </div>
          </div>
        </Card>

        <Card title="Approval Actions" subtitle="Make a decision on the current workflow step.">
          <div className="space-y-4">
            <div>
              <label htmlFor="revisionNotes" className="block text-sm font-medium text-zinc-700 mb-1">
                Revision Notes (Optional)
              </label>
              <textarea
                id="revisionNotes"
                rows={4}
                className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-zinc-400"
                placeholder="Enter notes if requesting a revision..."
                value={revisionNotes}
                onChange={(e) => setRevisionNotes(e.target.value)}
                disabled={status === 'approved' || status === 'rejected'}
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <Button 
                variant="primary" 
                onClick={() => handleDecision('approved')}
                disabled={status === 'approved'}
                className="bg-green-600 hover:bg-green-700 focus:ring-green-500"
              >
                Approve
              </Button>
              <Button 
                variant="danger" 
                onClick={() => handleDecision('rejected')}
                disabled={status === 'rejected'}
              >
                Reject
              </Button>
              <Button 
                variant="outline" 
                onClick={() => handleDecision('revision_requested')}
                disabled={status === 'revision_requested'}
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
