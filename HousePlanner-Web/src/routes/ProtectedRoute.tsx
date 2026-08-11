import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import useAuth from '../features/auth/useAuth';
import type { UserRole } from '../types/auth.types';
import Spinner from '../components/common/Spinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, user, isLoading } = useAuth();
  const location = useLocation();

  // If auth is loading (e.g. initial Firebase state resolution)
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50/50">
        <Spinner size="lg" />
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check if role is allowed for this route
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect to dashboard (or a general access denied page)
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
