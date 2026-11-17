import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import {
  LoginPage,
  SignUpPage,
  ForgotPasswordPage,
  ResetPasswordPage,
  OnboardingPage,
} from './pages/auth/AuthPages';

// Lazy-loaded application pages for route-level code splitting & bundle optimization
const OverviewDashboard = lazy(() =>
  import('./pages/dashboard/OverviewDashboard').then((m) => ({ default: m.OverviewDashboard }))
);
const DataSourcesOverview = lazy(() =>
  import('./pages/data-sources/DataSourcesOverview').then((m) => ({ default: m.DataSourcesOverview }))
);
const ConnectionDetail = lazy(() =>
  import('./pages/data-sources/ConnectionDetail').then((m) => ({ default: m.ConnectionDetail }))
);
const DashboardList = lazy(() =>
  import('./pages/dashboards/DashboardList').then((m) => ({ default: m.DashboardList }))
);
const DashboardEditor = lazy(() =>
  import('./pages/dashboards/DashboardEditor').then((m) => ({ default: m.DashboardEditor }))
);
const AutoDashboardWizard = lazy(() =>
  import('./pages/dashboards/AutoDashboardWizard').then((m) => ({ default: m.AutoDashboardWizard }))
);
const DataPreparationList = lazy(() =>
  import('./pages/data-prep/DataPreparationList').then((m) => ({ default: m.DataPreparationList }))
);
const DataPreparationEditor = lazy(() =>
  import('./pages/data-prep/DataPreparationEditor').then((m) => ({ default: m.DataPreparationEditor }))
);
const DataStudio = lazy(() =>
  import('./pages/data/DataStudio').then((m) => ({ default: m.DataStudio }))
);
const DatasetDetail = lazy(() =>
  import('./pages/data/DatasetDetail').then((m) => ({ default: m.DatasetDetail }))
);
const AskYourData = lazy(() =>
  import('./pages/ask/AskYourData').then((m) => ({ default: m.AskYourData }))
);
const AdvancedAnalyticsPage = lazy(() =>
  import('./pages/analytics/AdvancedAnalyticsPage').then((m) => ({ default: m.AdvancedAnalyticsPage }))
);
const PromptLabOverview = lazy(() =>
  import('./pages/prompt-lab/PromptLabOverview').then((m) => ({ default: m.PromptLabOverview }))
);
const ExperimentDetail = lazy(() =>
  import('./pages/prompt-lab/ExperimentDetail').then((m) => ({ default: m.ExperimentDetail }))
);
const ReportBuilder = lazy(() =>
  import('./pages/reports/ReportBuilder').then((m) => ({ default: m.ReportBuilder }))
);
const ReportsLibrary = lazy(() =>
  import('./pages/reports/ReportsLibrary').then((m) => ({ default: m.ReportsLibrary }))
);
const ReportPreview = lazy(() =>
  import('./pages/reports/ReportPreview').then((m) => ({ default: m.ReportPreview }))
);
const ReportHistory = lazy(() =>
  import('./pages/reports/ReportHistory').then((m) => ({ default: m.ReportHistory }))
);
const SettingsPage = lazy(() =>
  import('./pages/settings/SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const WorkspaceMembers = lazy(() =>
  import('./pages/workspaces/WorkspaceMembers').then((m) => ({ default: m.WorkspaceMembers }))
);
const WorkspaceActivityPage = lazy(() =>
  import('./pages/activity/WorkspaceActivityPage').then((m) => ({ default: m.WorkspaceActivityPage }))
);
const EnterpriseSecurityPage = lazy(() =>
  import('./pages/governance/EnterpriseSecurityPage').then((m) => ({ default: m.EnterpriseSecurityPage }))
);
const DataAutomationPage = lazy(() =>
  import('./pages/automation/DataAutomationPage').then((m) => ({ default: m.DataAutomationPage }))
);
const BusinessAnalystCenter = lazy(() =>
  import('./pages/business-analyst/BusinessAnalystCenter').then((m) => ({ default: m.BusinessAnalystCenter }))
);
const AcceptInvitation = lazy(() =>
  import('./pages/auth/AcceptInvitation').then((m) => ({ default: m.AcceptInvitation }))
);

const PageLoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-[60vh]">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 rounded-full border-2 border-[#009F98] border-t-transparent animate-spin" />
      <span className="text-xs text-[#52616C] font-medium">Loading workspace module...</span>
    </div>
  </div>
);

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageLoadingFallback />}>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/invitations/accept" element={<AcceptInvitation />} />

            {/* Authenticated Application Shell */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<OverviewDashboard />} />

              {/* Enterprise External Data Sources */}
              <Route path="/data-sources" element={<DataSourcesOverview />} />
              <Route path="/data-sources/:connectionId" element={<ConnectionDetail />} />

              {/* Interactive Dashboards */}
              <Route path="/dashboards" element={<DashboardList />} />
              <Route path="/dashboards/auto-generate" element={<AutoDashboardWizard />} />
              <Route path="/dashboards/:dashboardId" element={<DashboardEditor />} />

              {/* Data Preparation & Transformation Engine */}
              <Route path="/data-preparation" element={<DataPreparationList />} />
              <Route path="/data-preparation/:pipelineId" element={<DataPreparationEditor />} />

              {/* Data Studio */}
              <Route path="/data" element={<DataStudio />} />
              <Route path="/data/:datasetId" element={<DatasetDetail />} />

              {/* Ask Your Data */}
              <Route path="/ask" element={<AskYourData />} />

              {/* AI Business Analyst & Autonomous Insights (Phase 6D) */}
              <Route path="/business-analyst" element={<BusinessAnalystCenter />} />

              {/* Advanced Analytics & ML */}
              <Route path="/advanced-analytics" element={<AdvancedAnalyticsPage />} />

              {/* Prompt Lab */}
              <Route path="/prompt-lab" element={<PromptLabOverview />} />
              <Route path="/prompt-lab/experiments/:id" element={<ExperimentDetail />} />

              {/* Reports */}
              <Route path="/reports" element={<ReportsLibrary />} />
              <Route path="/reports/new" element={<ReportBuilder />} />
              <Route path="/reports/:reportId" element={<ReportPreview />} />
              <Route path="/reports/:reportId/preview" element={<ReportPreview />} />
              <Route path="/reports/:reportId/history" element={<ReportHistory />} />

              {/* Team Collaboration & Workspace Sharing */}
              <Route path="/workspaces/members" element={<WorkspaceMembers />} />
              <Route path="/activity" element={<WorkspaceActivityPage />} />

              {/* Enterprise Governance, RBAC & Security (Phase 5C) */}
              <Route path="/governance" element={<EnterpriseSecurityPage />} />

              {/* Data Automation, Scheduled Refresh & Jobs (Phase 5D) */}
              <Route path="/automation" element={<DataAutomationPage />} />

              {/* Settings */}
              <Route path="/settings" element={<SettingsPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
