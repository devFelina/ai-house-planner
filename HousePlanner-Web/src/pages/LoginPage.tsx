import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, KeyRound, Mail, AlertCircle } from 'lucide-react';
import useAuth from '../features/auth/useAuth';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import Card from '../components/common/Card';

export const LoginPage: React.FC = () => {
  const { login, isLoading, error: authError } = useAuth();
  const navigate = useNavigate();

  // Local Form State
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  // Validation Errors
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const validate = () => {
    const tempErrors: { email?: string; password?: string } = {};
    let isValid = true;

    if (!email.trim()) {
      tempErrors.email = 'Email address is required.';
      isValid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      tempErrors.email = 'Please enter a valid email address.';
      isValid = false;
    }

    if (!password) {
      tempErrors.password = 'Password is required.';
      isValid = false;
    } else if (password.length < 6) {
      tempErrors.password = 'Password must be at least 6 characters.';
      isValid = false;
    }

    setErrors(tempErrors);
    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmissionError(null);

    if (!validate()) return;

    try {
      await login(email, password);
      // On success, redirect to dashboard
      navigate('/dashboard');
    } catch (err: any) {
      setSubmissionError(err.message || 'Authentication failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-zinc-50/50">
      <div className="w-full max-w-md space-y-8">
        {/* App Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 bg-indigo-600 rounded-2xl text-white shadow-lg shadow-indigo-600/10 mb-2">
            <LogIn size={28} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-950">
            Welcome back to HousePlanner
          </h1>
          <p className="text-sm text-zinc-500">
            Sign in to access your Architect or Contractor dashboard
          </p>
        </div>

        {/* Login Card */}
        <Card className="custom-shadow-lg border-zinc-200/50 p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Field */}
            <div className="relative">
              <Input
                id="login-email"
                type="email"
                label="Email Address"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={errors.email}
                disabled={isLoading}
                className="pl-9"
              />
              <Mail 
                className="absolute top-[38px] left-3 text-zinc-400" 
                size={16} 
              />
            </div>

            {/* Password Field */}
            <div className="relative">
              <Input
                id="login-password"
                type="password"
                label="Password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                error={errors.password}
                disabled={isLoading}
                className="pl-9"
              />
              <KeyRound 
                className="absolute top-[38px] left-3 text-zinc-400" 
                size={16} 
              />
            </div>

            {/* Error Message Box */}
            {(submissionError || authError) && (
              <div className="flex items-start gap-2.5 p-3.5 bg-red-50 border border-red-100 rounded-lg text-red-700 text-xs font-medium">
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <span>{submissionError || authError}</span>
              </div>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              isLoading={isLoading}
              className="w-full mt-2"
            >
              Sign In
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
