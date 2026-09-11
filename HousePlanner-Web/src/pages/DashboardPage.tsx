import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Plus, Sparkles } from 'lucide-react';
import useAuth from '../features/auth/useAuth';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-[calc(100vh-65px)] bg-gradient-to-br from-zinc-50 to-zinc-100 flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background Decorative Elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-200/40 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob"></div>
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-purple-200/40 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-1/3 w-96 h-96 bg-pink-200/40 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob animation-delay-4000"></div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative z-10 bg-white/80 backdrop-blur-xl p-12 rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white/60 max-w-2xl w-full text-center"
      >
        <div className="mx-auto w-16 h-16 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-2xl flex items-center justify-center mb-6 shadow-inner border border-white">
          <Sparkles className="text-indigo-600" size={28} />
        </div>
        
        <h1 className="text-4xl font-bold text-zinc-900 mb-3 tracking-tight">
          Welcome back, {user?.fullName?.split(' ')[0] || 'Architect'}
        </h1>
        <p className="text-zinc-500 mb-10 text-lg font-medium">
          Ready to design something extraordinary today?
        </p>

        <div className="flex justify-center">
          <Link to="/dashboard/new-project">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="group relative flex items-center gap-3 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white rounded-2xl font-semibold shadow-[0_1px_2px_rgba(0,0,0,0.24)] transition-all overflow-hidden"
            >
              <div className="absolute inset-0 w-1/4 h-full bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12 -translate-x-full group-hover:animate-shine"></div>
              <Plus size={20} className="text-zinc-300 group-hover:text-white transition-colors" />
              <span>Start New Project</span>
            </motion.button>
          </Link>
        </div>
      </motion.div>
    </div>
  );
};

export default DashboardPage;
