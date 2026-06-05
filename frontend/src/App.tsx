/**
 * App.tsx
 * --------
 * Componente raíz de Frotis AI.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider }    from './contexts/AuthContext';
import { ToastProvider }   from './contexts/ToastContext';
import AppLayout           from './components/AppLayout/AppLayout';
import ProtectedRoute      from './components/ProtectedRoute/ProtectedRoute';
import LoginPage           from './pages/LoginPage/LoginPage';
import DashboardPage       from './pages/DashboardPage/DashboardPage';
import WorkspacePage       from './pages/WorkspacePage/WorkspacePage';
import AnalysisDetailPage  from './pages/AnalysisDetailPage/AnalysisDetailPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Ruta pública */}
            <Route path="/login" element={<LoginPage />} />

            {/* Rutas protegidas */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/dashboard"         element={<DashboardPage />} />
                <Route path="/workspace"          element={<WorkspacePage />} />
                <Route path="/analysis/:id"       element={<AnalysisDetailPage />} />
              </Route>
            </Route>

            {/* Redireccionamientos */}
            <Route path="/"  element={<Navigate to="/dashboard" replace />} />
            <Route path="*"  element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
