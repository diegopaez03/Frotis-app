/**
 * components/Sidebar/Sidebar.tsx
 * --------------------------------
 * Navegación lateral principal de la aplicación.
 */

import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import './Sidebar.css';

interface NavItem {
  to:    string;
  icon:  string;
  label: string;
  title: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    to:    '/dashboard',
    icon:  '◈',
    label: 'Dashboard',
    title: 'Historial de análisis',
  },
  {
    to:    '/workspace',
    icon:  '⊕',
    label: 'Nuevo análisis',
    title: 'Iniciar análisis de frotis',
  },
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const { showToast }    = useToast();
  const navigate         = useNavigate();

  function handleLogout(): void {
    logout();
    showToast('info', 'Sesión cerrada', 'Has cerrado sesión correctamente.');
    if (onClose) onClose();
    void navigate('/login');
  }

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : '??';

  return (
    <aside className={`sidebar${isOpen ? ' is-open' : ''}`} role="navigation" aria-label="Navegación principal">
      {/* Close button for mobile */}
      <button
        className="sidebar-close-btn"
        onClick={onClose}
        aria-label="Cerrar menú de navegación"
      >
        ✕
      </button>
      {/* Logo */}
      <div className="sidebar-logo" aria-label="Frotis AI">
        <div className="sidebar-logo-icon" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="28" r="16" stroke="var(--color-primary-container)" strokeWidth="4" />
            <circle cx="32" cy="28" r="7"  fill="var(--color-primary-container)" opacity="0.7" />
            <line x1="32" y1="12" x2="32" y2="6"  stroke="var(--color-primary-container)" strokeWidth="3" strokeLinecap="round"/>
            <line x1="32" y1="44" x2="32" y2="56" stroke="var(--color-primary-container)" strokeWidth="3" strokeLinecap="round"/>
            <line x1="25" y1="52" x2="39" y2="52" stroke="var(--color-primary-container)" strokeWidth="3" strokeLinecap="round"/>
          </svg>
        </div>
        <span className="sidebar-logo-text">Frotis AI</span>
      </div>

      <span className="sidebar-section-label">Navegación</span>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon, label, title }) => (
          <NavLink
            key={to}
            to={to}
            title={title}
            onClick={onClose}
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' sidebar-link-active' : ''}`
            }
          >
            <span className="sidebar-link-icon" aria-hidden="true">{icon}</span>
            <span className="sidebar-link-label">{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-spacer" />

      <div className="sidebar-user">
        <div className="avatar" aria-hidden="true">{initials}</div>
        <div className="sidebar-user-info">
          <p className="sidebar-user-email" title={user?.email ?? undefined}>
            {user?.email}
          </p>
          <button
            className="sidebar-logout-btn"
            onClick={handleLogout}
            id="sidebar-logout-btn"
          >
            Cerrar sesión
          </button>
        </div>
      </div>
    </aside>
  );
}
