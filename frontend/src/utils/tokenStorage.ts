/**
 * utils/tokenStorage.ts
 * ---------------------
 * Gestión segura del JWT en el cliente mediante cookies persistentes.
 *
 * Estrategia de seguridad:
 *   - Se persiste en cookies con Max-Age de 2 semanas (14 días)
 *   - Validación de formato JWT antes de almacenar
 *   - Decodificación del payload para verificar expiración
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
// Helpers privados de Cookies
// ---------------------------------------------------------------------------

function setCookie(name: string, value: string, days: number): void {
  const maxAge = days * 24 * 60 * 60;
  // Almacenar cookie con max-age de 2 semanas (14 días) y path raíz
  document.cookie = `${name}=${encodeURIComponent(value)}; max-age=${maxAge}; path=/; samesite=lax`;
}

function getCookie(name: string): string | null {
  const nameEQ = name + '=';
  const ca = document.cookie.split(';');
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length, c.length));
  }
  return null;
}

function eraseCookie(name: string): void {
  document.cookie = `${name}=; max-age=0; path=/; samesite=lax`;
}

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
    setCookie(TOKEN_KEY, token.trim(), 14); // 2 semanas (14 días)
  },

  getToken(): string | null {
    const token = getCookie(TOKEN_KEY);
    if (!token || !isValidJwtFormat(token)) return null;
    return token;
  },

  removeToken(): void {
    eraseCookie(TOKEN_KEY);
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
      setCookie(USER_KEY, JSON.stringify(safeUser), 14); // 2 semanas (14 días)
    } catch { /* no-op */ }
  },

  getUser(): StoredUser | null {
    try {
      const raw = getCookie(USER_KEY);
      return raw ? (JSON.parse(raw) as StoredUser) : null;
    } catch {
      return null;
    }
  },

  removeUser(): void {
    eraseCookie(USER_KEY);
  },
};

// ---------------------------------------------------------------------------
// Limpieza completa (logout)
// ---------------------------------------------------------------------------

export function clearSession(): void {
  tokenStorage.removeToken();
  userStorage.removeUser();
}
