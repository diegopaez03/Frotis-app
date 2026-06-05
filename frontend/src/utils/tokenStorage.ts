/**
 * utils/tokenStorage.ts
 * ---------------------
 * Gestión segura del JWT en el cliente.
 *
 * Estrategia de seguridad:
 *   - Se persiste en sessionStorage (expira al cerrar pestaña)
 *   - Validación de formato JWT antes de almacenar
 *   - Decodificación del payload para verificar expiración
 *   - NUNCA se almacena en localStorage ni cookies sin HttpOnly
 */

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const TOKEN_KEY = 'frotis_access_token';
const USER_KEY  = 'frotis_user_data';

/** Regex: tres segmentos Base64url separados por puntos */
const JWT_FORMAT = /^[\w-]+\.[\w-]+\.[\w-]+$/;

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export interface StoredUser {
  id: string;
  email: string;
  fechaCreacion: string;
}

interface JwtPayload {
  sub?: string;
  exp?: number;
  iat?: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Helpers privados
// ---------------------------------------------------------------------------

function isValidJwtFormat(token: string): boolean {
  return typeof token === 'string' && JWT_FORMAT.test(token.trim());
}

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const base64 = token.split('.')[1];
    const padded  = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      '='
    );
    return JSON.parse(atob(padded.replace(/-/g, '+').replace(/_/g, '/'))) as JwtPayload;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// tokenStorage — gestión del JWT
// ---------------------------------------------------------------------------

export const tokenStorage = {
  setToken(token: string): void {
    if (!isValidJwtFormat(token)) {
      console.warn('[tokenStorage] Formato JWT inválido. Token no almacenado.');
      return;
    }
    try {
      sessionStorage.setItem(TOKEN_KEY, token.trim());
    } catch (e) {
      console.warn('[tokenStorage] sessionStorage no disponible:', (e as Error).message);
    }
  },

  getToken(): string | null {
    try {
      const token = sessionStorage.getItem(TOKEN_KEY);
      if (!token || !isValidJwtFormat(token)) return null;
      return token;
    } catch {
      return null;
    }
  },

  removeToken(): void {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch { /* no-op */ }
  },

  hasValidToken(): boolean {
    const token = this.getToken();
    if (!token) return false;

    const payload = decodeJwtPayload(token);
    if (!payload?.exp) return false;

    const nowSeconds = Math.floor(Date.now() / 1000);
    return payload.exp > nowSeconds + 30;
  },

  getTokenPayload(): JwtPayload | null {
    const token = this.getToken();
    if (!token) return null;
    return decodeJwtPayload(token);
  },
};

// ---------------------------------------------------------------------------
// userStorage — datos no sensibles del usuario para la UI
// ---------------------------------------------------------------------------

export const userStorage = {
  setUser(user: StoredUser): void {
    try {
      const safeUser: StoredUser = {
        id:            user.id,
        email:         user.email,
        fechaCreacion: user.fechaCreacion,
      };
      sessionStorage.setItem(USER_KEY, JSON.stringify(safeUser));
    } catch { /* no-op */ }
  },

  getUser(): StoredUser | null {
    try {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as StoredUser) : null;
    } catch {
      return null;
    }
  },

  removeUser(): void {
    try {
      sessionStorage.removeItem(USER_KEY);
    } catch { /* no-op */ }
  },
};

// ---------------------------------------------------------------------------
// Limpieza completa (logout)
// ---------------------------------------------------------------------------

export function clearSession(): void {
  tokenStorage.removeToken();
  userStorage.removeUser();
}
