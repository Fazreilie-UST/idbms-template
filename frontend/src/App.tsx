const AuditLogsPage = lazy(() => import("@/features/auditLogs"));
const LogReportsPage = lazy(() => import("@/features/logReports"));
const DevLogReportsPage = lazy(() => import("@/features/logReports/DevLogReportsPage"));
const BugReportView = lazy(() => import("@/features/logReports/BugReportView"));
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Spin } from "antd";

import ProtectedRoute from "@/shared/routes/ProtectedRoute";
import MainLayout from "@/shared/layouts/MainLayout";
import ErrorBoundary from "@/shared/components/ErrorBoundary";

// Login is small but still loads upfront (it's the landing page).
const Login = lazy(() => import("@/features/auth/pages/Login"));
const AccountSettings = lazy(() => import("@/features/auth/pages/AccountSettings"));

// Dashboards
const PMDashboard = lazy(() => import("@/features/dashboards/pages/PM_Dashboard"));
const RequestorDashboard = lazy(
  () => import("@/features/dashboards/pages/Requestor_Dashboard"),
);

// Build plans
const BuildPlanManager = lazy(() => import("@/features/buildplans/pages/BuildPlanManager"));
const BuildplanView = lazy(() => import("@/features/buildplans/pages/BuildplanView"));
const BuildPlanTracker = lazy(() => import("@/features/buildplans/pages/BuildPlanTracker"));
const BuildPlanImport = lazy(() => import("@/features/buildplans/pages/BuildPlanImport"));

// Build requests
const BuildRequestManager = lazy(
  () => import("@/features/orders/pages/BuildRequestManager"),
);
const BuildRequestView = lazy(() => import("@/features/orders/pages/BuildRequestView"));
const BuildRequestTracker = lazy(
  () => import("@/features/orders/pages/BuildRequestTracker"),
);

// Shipments
const ShippingManager = lazy(() => import("@/features/shipments/pages/ShippingManager"));
const ShippingView = lazy(() => import("@/features/shipments/pages/ShippingView"));
const ShippingTracker = lazy(() => import("@/features/shipments/pages/ShippingTracker"));
const ShippingImport = lazy(() => import("@/features/shipments/pages/ShippingImport"));

// Admin
const UserManagement = lazy(() => import("@/features/admin/pages/UserManagement"));
const RoleManagement = lazy(() => import("@/features/admin/pages/RoleManagement"));
const DBTablesManagement = lazy(
  () => import("@/features/admin/pages/DBTablesManagement"),
);

// Documentation
const DocumentationPage = lazy(
  () => import("@/features/documentation/pages/DocumentationPage"),
);

function PageFallback() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "60vh",
      }}
    >
      <Spin size="large" />
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<Login />} />

            {/* Program Manager only */}
            <Route element={<ProtectedRoute allowedRoles={["Program Manager"]} />}>
              <Route element={<MainLayout />}>
                <Route path="/pm/dashboard" element={<PMDashboard />} />

                <Route path="/pm/build-plans" element={<BuildPlanManager />} />
                <Route path="/pm/build-plans/:id" element={<BuildplanView />} />

                <Route path="/pm/build-requests" element={<BuildRequestManager />} />
                <Route path="/pm/build-requests/:id" element={<BuildRequestView />} />

                <Route path="/pm/shippings" element={<ShippingManager />} />
                <Route path="/pm/shippings/:id" element={<ShippingView />} />

                <Route path="/pm/admin/import-build-plan" element={<BuildPlanImport />} />
                <Route path="/pm/admin/import-shipments" element={<ShippingImport />} />
                <Route path="/pm/admin/users" element={<UserManagement />} />
                <Route path="/pm/admin/roles" element={<RoleManagement />} />
                <Route path="/pm/admin/db-tables" element={<DBTablesManagement />} />
              </Route>
            </Route>

            {/* Requestor only */}
            <Route element={<ProtectedRoute allowedRoles={["Requestor"]} />}>
              <Route element={<MainLayout />}>
                <Route path="/requestor/dashboard" element={<RequestorDashboard />} />
                <Route
                  path="/requestor/build-requests"
                  element={<BuildRequestManager />}
                />
                <Route
                  path="/requestor/build-requests/:id"
                  element={<BuildRequestView />}
                />
              </Route>
            </Route>



            {/* Shared tracker pages and logs/reports - all roles can access */}
            <Route
              element={
                <ProtectedRoute allowedRoles={["Program Manager", "Requestor", "Admin", "Developer"]} />
              }
            >
              <Route element={<MainLayout />}>
                <Route path="/build-plan-tracker" element={<BuildPlanTracker />} />
                <Route path="/build-plan-tracker/:id" element={<BuildplanView />} />
                <Route path="/build-request-tracker" element={<BuildRequestTracker />} />
                <Route
                  path="/build-request-tracker/:id"
                  element={<BuildRequestView />}
                />
                <Route path="/shipment-tracker" element={<ShippingTracker />} />
                <Route path="/account" element={<AccountSettings />} />
                <Route path="/documentation" element={<DocumentationPage />} />
                {/* Audit & Logs: Admin only */}
                <Route element={<ProtectedRoute allowedRoles={["Admin"]} />}>
                  <Route path="/logs/audit" element={<AuditLogsPage />} />
                  <Route path="/logs/bug-reports" element={<DevLogReportsPage />} />
                  <Route path="/logs/bug-reports/:reportId" element={<BugReportView />} />
                </Route>
                {/* All roles: Report an Issue */}
                <Route path="/logs/reports" element={<LogReportsPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
            {/* Logs & Reports Section */}
            {/* Admin/Dev: Audit Logs and All Reports */}
            <Route element={<ProtectedRoute allowedRoles={["Admin", "Developer"]} />}>
              <Route path="/admin/audit-logs" element={<AuditLogsPage />} />
              <Route path="/admin/log-reports" element={<DevLogReportsPage />} />
            </Route>
            {/* All users: Submit Report */}
            <Route element={<ProtectedRoute allowedRoles={["Requestor", "Program Manager", "Admin", "Developer"]} />}>
              <Route path="/reports/submit" element={<LogReportsPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
