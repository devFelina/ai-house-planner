import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';
import DashboardPage from '../pages/DashboardPage';
import ProtectedRoute from './ProtectedRoute';
import PageContainer from '../components/layout/PageContainer';
import IntakeForm from '../pages/IntakeForm';
import HomePage from '../pages/HomePage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<HomePage />} />
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
        path="/dashboard/new-project"
        element={
          <ProtectedRoute>
            <PageContainer>
              <IntakeForm/>
            </PageContainer>
          </ProtectedRoute>
        }
      />

      {/* Fallback routing */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
