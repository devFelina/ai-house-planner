import React from 'react';
import { motion } from 'framer-motion';

const DashboardPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="bg-white p-12 rounded-3xl shadow-sm border border-gray-100 max-w-2xl w-full text-center"
      >
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Welcome to your Dashboard</h1>
        <p className="text-gray-500 mb-8">This is a placeholder for the dashboard. Your projects and AI designs will appear here.</p>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-32 bg-gray-50 rounded-2xl border border-dashed border-gray-200 flex items-center justify-center text-gray-400">
            Active Project
          </div>
          <div className="h-32 bg-gray-50 rounded-2xl border border-dashed border-gray-200 flex items-center justify-center text-gray-400">
            Cost Estimates
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default DashboardPage;
