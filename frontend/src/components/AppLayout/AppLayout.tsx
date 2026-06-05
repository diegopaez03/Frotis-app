/**
 * components/AppLayout/AppLayout.tsx
 * ------------------------------------
 * Layout principal de la aplicación autenticada.
 */

import { Outlet } from 'react-router-dom';
import Sidebar from '../Sidebar/Sidebar';
import './AppLayout.css';

export default function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main" id="main-content">
        <Outlet />
      </main>
    </div>
  );
}
