import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Plus, Sparkles } from 'lucide-react';
import useAuth from '../features/auth/useAuth';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-[calc(100vh-65px)] flex items-center justify-center p-6 relative overflow-hidden transition-colors duration-300">
      {/* Background Decorative Elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-200/40 dark:bg-indigo-900/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-50 animate-blob"></div>
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-purple-200/40 dark:bg-purple-900/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-50 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-1/3 w-96 h-96 bg-pink-200/40 dark:bg-pink-900/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-50 animate-blob animation-delay-4000"></div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl p-12 rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.2)] border border-white/60 dark:border-gray-700/50 max-w-2xl w-full text-center transition-colors duration-300"
      >
        <div className="mx-auto w-16 h-16 bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/50 dark:to-purple-900/50 rounded-2xl flex items-center justify-center mb-6 shadow-inner border border-white dark:border-gray-800">
          <Sparkles className="text-indigo-600 dark:text-indigo-400" size={28} />
        </div>
        
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-white mb-3 tracking-tight transition-colors">
          Welcome back, {user?.fullName?.split(' ')[0] || 'Architect'}
        </h1>
        <p className="text-zinc-500 dark:text-gray-400 mb-10 text-lg font-medium transition-colors">
          Ready to design something extraordinary today?
        </p>

        <div className="flex justify-center">
          <Link to="/dashboard/new-project">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="group relative flex items-center gap-3 px-8 py-4 bg-zinc-900 dark:bg-white hover:bg-zinc-800 dark:hover:bg-gray-200 text-white dark:text-zinc-900 rounded-2xl font-semibold shadow-[0_1px_2px_rgba(0,0,0,0.24)] transition-all overflow-hidden"
            >
              <div className="absolute inset-0 w-1/4 h-full bg-gradient-to-r from-transparent via-white/10 dark:via-black/10 to-transparent -skew-x-12 -translate-x-full group-hover:animate-shine"></div>
              <Plus size={20} className="text-zinc-300 dark:text-zinc-600 group-hover:text-white dark:group-hover:text-zinc-900 transition-colors" />
              <span>Start New Project</span>
            </motion.button>
          </Link>
        </div>
      </motion.div>
    </div>
  );
};

export default DashboardPage;
