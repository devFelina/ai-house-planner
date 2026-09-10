import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';
import DashboardPage from '../pages/DashboardPage';
import ProtectedRoute from './ProtectedRoute';
import PageContainer from '../components/layout/PageContainer';
import ApprovalPage from '../pages/ApprovalPage';
import ProjectTrackingPage from '../pages/ProjectTrackingPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <PageContainer>
              <DashboardPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />
      <Route
        path="/approval"
        element={
          <ProtectedRoute>
            <PageContainer>
              <ApprovalPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />
      <Route
        path="/project-tracking"
        element={
          <ProtectedRoute>
            <PageContainer>
              <ProjectTrackingPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      {/* Fallback routing */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default AppRoutes;
