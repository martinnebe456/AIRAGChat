import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { ChatRouteShell } from "../components/ChatRouteShell";
import { RequireAuth } from "../components/RequireAuth";
import { RequireRole } from "../components/RequireRole";
import { LoginPage } from "../pages/LoginPage";
import { ChatPage } from "../pages/ChatPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import { ProfilePage } from "../pages/ProfilePage";
import { AdminUsersPage } from "../pages/AdminUsersPage";
import { AdminProjectsPage } from "../pages/AdminProjectsPage";
import { AdminSettingsPage } from "../pages/AdminSettingsPage";
import { AdminEvalDatasetsPage } from "../pages/AdminEvalDatasetsPage";
import { AdminEvalRunPage } from "../pages/AdminEvalRunPage";
import { AdminEvalResultsPage } from "../pages/AdminEvalResultsPage";
import { AdminEmbeddingsReindexPage } from "../pages/AdminEmbeddingsReindexPage";

function ProtectedLayout() {
  return (
    <RequireAuth>
      <AppLayout>
        <Outlet />
      </AppLayout>
    </RequireAuth>
  );
}

function ProtectedChatLayout() {
  return (
    <RequireAuth>
      <ChatRouteShell>
        <Outlet />
      </ChatRouteShell>
    </RequireAuth>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedChatLayout />}>
        <Route path="/chat" element={<ChatPage />} />
      </Route>
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/profile" element={<ProfilePage />} />

        <Route
          path="/admin/users"
          element={
            <RequireRole roles={["admin"]}>
              <AdminUsersPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/projects"
          element={
            <RequireRole roles={["admin"]}>
              <AdminProjectsPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <RequireRole roles={["admin"]}>
              <AdminSettingsPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/embeddings/reindex"
          element={
            <RequireRole roles={["admin"]}>
              <AdminEmbeddingsReindexPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/evals/datasets"
          element={
            <RequireRole roles={["admin"]}>
              <AdminEvalDatasetsPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/evals/run"
          element={
            <RequireRole roles={["admin"]}>
              <AdminEvalRunPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/evals/results"
          element={
            <RequireRole roles={["admin"]}>
              <AdminEvalResultsPage />
            </RequireRole>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}
