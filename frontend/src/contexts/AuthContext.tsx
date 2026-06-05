/**
 * contexts/AuthContext.tsx
 * -------------------------
 * Contexto global de autenticación para Frotis AI.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import { authAPI } from '../services/api';
import { tokenStorage, userStorage, clearSession, StoredUser } from '../utils/tokenStorage';
import type { UserCreate, LoginRequest } from '../types/api';

// ---------------------------------------------------------------------------
// Tipos del contexto
// ---------------------------------------------------------------------------

interface AuthContextValue {
  user:            StoredUser | null;
  isAuthenticated: boolean;
  isLoading:       boolean;
  login:           (credentials: LoginRequest) => Promise<StoredUser>;
  register:        (data: UserCreate) => Promise<StoredUser>;
  logout:          () => void;
}

// ---------------------------------------------------------------------------
// Contexto
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user,      setUser]      = useState<StoredUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ------------------------------------------------------------------
  // Restaurar sesión al montar
  // ------------------------------------------------------------------
  useEffect(() => {
    async function restoreSession(): Promise<void> {
      if (!tokenStorage.hasValidToken()) {
        setIsLoading(false);
        return;
      }

      const cached = userStorage.getUser();
      if (cached) {
        setUser(cached);
        setIsLoading(false);
        return;
      }

      try {
        const me = await authAPI.getMe();
        const storedUser: StoredUser = {
          id:            me.id,
          email:         me.email,
          fechaCreacion: me.fechaCreacion,
        };
        setUser(storedUser);
        userStorage.setUser(storedUser);
      } catch {
        clearSession();
      } finally {
        setIsLoading(false);
      }
    }

    void restoreSession();
  }, []);

  // ------------------------------------------------------------------
  // Escuchar evento de expiración de token
  // ------------------------------------------------------------------
  useEffect(() => {
    const handleExpiry = (): void => {
      setUser(null);
      clearSession();
    };
    window.addEventListener('auth:expired', handleExpiry);
    return () => window.removeEventListener('auth:expired', handleExpiry);
  }, []);

  // ------------------------------------------------------------------
  // Login
  // ------------------------------------------------------------------
  const login = useCallback(async (credentials: LoginRequest): Promise<StoredUser> => {
    const { access_token } = await authAPI.login(credentials);
    tokenStorage.setToken(access_token);

    const me = await authAPI.getMe();
    const storedUser: StoredUser = {
      id:            me.id,
      email:         me.email,
      fechaCreacion: me.fechaCreacion,
    };
    userStorage.setUser(storedUser);
    setUser(storedUser);
    return storedUser;
  }, []);

  // ------------------------------------------------------------------
  // Registro (crea cuenta + auto-login)
  // ------------------------------------------------------------------
  const register = useCallback(async (data: UserCreate): Promise<StoredUser> => {
    await authAPI.register(data);
    return login({ email: data.email, password: data.password });
  }, [login]);

  // ------------------------------------------------------------------
  // Logout
  // ------------------------------------------------------------------
  const logout = useCallback((): void => {
    clearSession();
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  return ctx;
}
