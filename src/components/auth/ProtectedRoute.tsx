import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F5F8FA] flex flex-col items-center justify-center p-6">
        <div className="flex items-end gap-1.5 mb-4 animate-pulse">
          <div className="w-2.5 h-5 bg-[#009F98] rounded-full animate-bounce [animation-delay:-0.3s]" />
          <div className="w-2.5 h-8 bg-[#39C3B8] rounded-full animate-bounce [animation-delay:-0.15s]" />
          <div className="w-2.5 h-10 bg-[#8BE5DE] rounded-full animate-bounce" />
        </div>
        <p className="text-xs font-semibold text-[#52616C]">Verifying secure session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

