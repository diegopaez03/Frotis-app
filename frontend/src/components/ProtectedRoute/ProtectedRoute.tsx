/**
 * components/ProtectedRoute/ProtectedRoute.tsx
 * ---------------------------------------------
 * Wrapper que protege rutas autenticadas.
 */

import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export default function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
          minHeight:      '100vh',
          background:     'var(--color-bg)',
          flexDirection:  'column',
          gap:            'var(--space-4)',
        }}
      >
        <div className="spinner spinner-lg" />
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-label-md)' }}>
          Verificando sesión…
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
