/**
 * main.tsx
 * ---------
 * Punto de entrada de la aplicación React con TypeScript.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './styles/design-tokens.css';
import './styles/globals.css';
import './styles/components.css';

import App from './App.tsx';

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('No se encontró el elemento #root en el DOM.');

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
