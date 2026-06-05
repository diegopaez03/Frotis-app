/**
 * contexts/ToastContext.tsx
 * --------------------------
 * Sistema global de notificaciones toast para Frotis AI.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  ReactNode,
} from 'react';
import '../styles/components.css';

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id:      number;
  type:    ToastType;
  title:   string;
  message: string;
}

interface ToastContextValue {
  showToast: (
    type:     ToastType,
    title:    string,
    message?: string,
    duration?: number
  ) => number;
}

// ---------------------------------------------------------------------------
// Contexto
// ---------------------------------------------------------------------------

const ToastContext = createContext<ToastContextValue | null>(null);

let toastIdCounter = 0;

const TOAST_ICONS: Record<ToastType, string> = {
  success: '✓',
  error:   '✕',
  warning: '⚠',
  info:    'ℹ',
};

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Record<number, ReturnType<typeof setTimeout>>>({});

  const removeToast = useCallback((id: number): void => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    if (timers.current[id]) {
      clearTimeout(timers.current[id]);
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete timers.current[id];
    }
  }, []);

  const showToast = useCallback(
    (
      type: ToastType = 'info',
      title: string,
      message = '',
      duration = 4500
    ): number => {
      const id = ++toastIdCounter;
      setToasts((prev) => [{ id, type, title, message }, ...prev].slice(0, 5));
      timers.current[id] = setTimeout(() => removeToast(id), duration);
      return id;
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-container" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.type}`} role="alert">
            <span className="toast-icon" aria-hidden="true">
              {TOAST_ICONS[toast.type]}
            </span>
            <div className="toast-content">
              <p className="toast-title">{toast.title}</p>
              {toast.message && <p className="toast-message">{toast.message}</p>}
            </div>
            <button
              className="btn-ghost"
              style={{ padding: '4px', borderRadius: 'var(--radius-sm)' }}
              onClick={() => removeToast(toast.id)}
              aria-label="Cerrar notificación"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast debe usarse dentro de <ToastProvider>');
  return ctx;
}
