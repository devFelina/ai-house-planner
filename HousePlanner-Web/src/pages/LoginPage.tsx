import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { motion } from 'framer-motion';
import { Box, Lock, Mail, ArrowRight } from 'lucide-react';
import { setMockAuth } from '../features/auth/authSlice';

const LoginPage: React.FC = () => {
  const [isHovered, setIsHovered] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Hardcoded auth requirement
    const validEmails = ['architect@houseplanner.com', 'contractor@houseplanner.com'];
    if (validEmails.includes(email) && password === 'password123') {
      dispatch(setMockAuth({
        uid: 'mock-123',
        email: email,
        role: email.startsWith('architect') ? 'Architect' : 'Contractor',
      } as any));
      navigate('/dashboard');
    } else {
      setError('Invalid email or password.');
    }
  };

  const handleGoogleLogin = () => {
    // Mock Google Login logic
    console.log("Initiating Google Login...");
    // Since Firebase config is not fully set up, we mock a successful google login
    setTimeout(() => {
      dispatch(setMockAuth({
        uid: 'mock-google-123',
        email: 'user@gmail.com',
        role: 'Architect',
      } as any));
      navigate('/dashboard');
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#fcfcfd] dark:bg-gray-950 flex items-center justify-center p-6 relative overflow-hidden transition-colors">
      
      {/* Decorative Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -right-[5%] w-[40%] h-[40%] rounded-full bg-blue-100/50 dark:bg-blue-900/20 blur-3xl"></div>
        <div className="absolute top-[60%] -left-[10%] w-[30%] h-[30%] rounded-full bg-indigo-100/40 dark:bg-indigo-900/20 blur-3xl"></div>
      </div>

      <Link to="/" className="absolute top-8 left-8 flex items-center gap-2 text-gray-900 dark:text-white hover:text-blue-600 transition-colors z-10">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Box className="text-white" size={18} />
        </div>
        <span className="text-lg font-bold tracking-tight">HomePlanner<span className="text-blue-600">AI</span></span>
      </Link>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="bg-white dark:bg-gray-900 rounded-3xl p-8 sm:p-10 custom-shadow-xl border border-gray-100 dark:border-gray-800 relative overflow-hidden">
          
          <div className="text-center mb-10">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Welcome Back</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Sign in to access your projects or admin portal.</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            
            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400 text-center">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 ml-1">Email Address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="block w-full pl-11 pr-4 py-3.5 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-xl text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all outline-none"
                  placeholder="name@example.com"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between ml-1">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
                <a href="#" className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">Forgot password?</a>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="block w-full pl-11 pr-4 py-3.5 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-xl text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all outline-none"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button 
              type="submit"
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              className="w-full bg-gray-900 dark:bg-white hover:bg-black dark:hover:bg-gray-200 text-white dark:text-gray-900 font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all custom-shadow-md group mt-8"
            >
              Sign In
              <motion.div
                animate={{ x: isHovered ? 4 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ArrowRight size={18} />
              </motion.div>
            </button>
          </form>

          <div className="my-6 flex items-center before:mt-0.5 before:flex-1 before:border-t before:border-gray-200 dark:before:border-gray-800 after:mt-0.5 after:flex-1 after:border-t after:border-gray-200 dark:after:border-gray-800">
            <p className="mx-4 mb-0 text-center text-xs text-gray-400 font-medium uppercase tracking-wider">
              Or
            </p>
          </div>

          <button 
            onClick={handleGoogleLogin}
            className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-white font-semibold py-3.5 rounded-xl flex items-center justify-center gap-3 transition-colors"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>

          <div className="mt-8 text-center text-sm text-gray-500">
            Don't have an account?{' '}
            <a href="#" className="font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400">Contact Administrator</a>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default LoginPage;
