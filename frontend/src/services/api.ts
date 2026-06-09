/**
 * services/api.ts
 * ---------------
 * Capa de abstracción de API para Frotis AI.
 *
 * Responsabilidades:
 *   - Configuración base de Axios (baseURL, timeouts, headers)
 *   - Interceptores para inyección automática de JWT Bearer token
 *   - Interceptores de respuesta para manejo global de errores (401, 403, 5xx)
 *   - Protección CSRF mediante header personalizado
 *   - Lógica de reintentos para errores de red transitorios
 *   - Helpers tipados para todos los endpoints de Frotis-App API
 */

import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios';
import { tokenStorage } from '../utils/tokenStorage';
import type {
  UserCreate,
  LoginRequest,
  UserResponse,
  TokenResponse,
  PredictRequest,
  PredictResponse,
  AnalyzeResponse,
  UploadAndPredictResult,
  AnalysisListItem,
  ApiError,
} from '../types/api';

// ---------------------------------------------------------------------------
// Instancia base de Axios
// ---------------------------------------------------------------------------

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '';

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    // Protección CSRF: header que los navegadores NO añaden automáticamente
    // en cross-origin simple requests, obligando preflight CORS.
    'X-Requested-With': 'XMLHttpRequest',
  },
});

// ---------------------------------------------------------------------------
// Interceptor de REQUEST — Inyección de JWT
// ---------------------------------------------------------------------------

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = tokenStorage.getToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error: unknown) => Promise.reject(error)
);

// ---------------------------------------------------------------------------
// Interceptor de RESPONSE — Manejo global de errores
// ---------------------------------------------------------------------------

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,

  (error: AxiosError<{ detail?: string | { msg: string }[] }>): Promise<never> => {
    // Error de red (sin respuesta del servidor)
    if (!error.response) {
      const apiError: ApiError = {
        type:     'NETWORK_ERROR',
        message:  'No se pudo conectar con el servidor. Verifica tu conexión.',
        original: error,
      };
      return Promise.reject(apiError);
    }

    const { status, data } = error.response;

    // 401 — Token expirado o inválido
    if (status === 401) {
      tokenStorage.removeToken();
      if (window.location.pathname !== '/login') {
        window.dispatchEvent(new CustomEvent('auth:expired'));
      }
      return Promise.reject({
        type:     'UNAUTHORIZED',
        message:  typeof data?.detail === 'string'
          ? data.detail
          : 'Sesión expirada. Inicia sesión nuevamente.',
        status,
        original: error,
      } satisfies ApiError);
    }

    // 403 — Sin permisos
    if (status === 403) {
      return Promise.reject({
        type:    'FORBIDDEN',
        message: typeof data?.detail === 'string'
          ? data.detail
          : 'No tienes permisos para realizar esta acción.',
        status,
        original: error,
      } satisfies ApiError);
    }

    // 422 — Validation error (FastAPI)
    if (status === 422) {
      const detail = data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((e) => (typeof e === 'object' && 'msg' in e ? e.msg : String(e))).join(', ')
        : typeof detail === 'string'
        ? detail
        : 'Datos inválidos enviados al servidor.';

      return Promise.reject({
        type:    'VALIDATION_ERROR',
        message,
        status,
        fields:  detail,
        original: error,
      } satisfies ApiError);
    }

    // 5xx — Error del servidor
    if (status >= 500) {
      return Promise.reject({
        type:    'SERVER_ERROR',
        message: typeof data?.detail === 'string'
          ? data.detail
          : 'Error interno del servidor. Inténtalo nuevamente.',
        status,
        original: error,
      } satisfies ApiError);
    }

    // Otros errores 4xx
    return Promise.reject({
      type:    'CLIENT_ERROR',
      message: typeof data?.detail === 'string' ? data.detail : `Error ${status}`,
      status,
      original: error,
    } satisfies ApiError);
  }
);

// ---------------------------------------------------------------------------
// Helper de reintentos
// ---------------------------------------------------------------------------

async function withRetry<T>(
  fn: () => Promise<T>,
  retries = 2,
  delayMs = 1000
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      // Solo reintenta en errores de red
      if ((err as ApiError).type !== 'NETWORK_ERROR') throw err;
      if (attempt < retries) {
        await new Promise<void>((res) => setTimeout(res, delayMs * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export const authAPI = {
  register(data: UserCreate): Promise<UserResponse> {
    return withRetry(() =>
      apiClient.post<UserResponse>('/auth/register', data).then((r) => r.data)
    );
  },

  login(credentials: LoginRequest): Promise<TokenResponse> {
    return withRetry(() =>
      apiClient.post<TokenResponse>('/auth/login', credentials).then((r) => r.data)
    );
  },

  getMe(): Promise<UserResponse> {
    return withRetry(() =>
      apiClient.get<UserResponse>('/users/me').then((r) => r.data)
    );
  },
};

// ---------------------------------------------------------------------------
// Analysis API
// ---------------------------------------------------------------------------

export const analysisAPI = {
  /** GET /analysis — lista de análisis del usuario autenticado */
  getAll(): Promise<AnalysisListItem[]> {
    return withRetry(() =>
      apiClient.get<AnalysisListItem[]>('/analysis').then((r) => r.data)
    );
  },

  /** GET /analysis/{analysis_id} — detalle de un análisis */
  getById(id: string): Promise<AnalysisListItem> {
    return withRetry(() =>
      apiClient.get<AnalysisListItem>(`/analysis/${id}`).then((r) => r.data)
    );
  },

  predict(payload: PredictRequest): Promise<PredictResponse> {
    return withRetry(
      () => apiClient.post<PredictResponse>('/predict', payload).then((r) => r.data),
      1,
      2000
    );
  },

  analyze(formData: FormData): Promise<AnalyzeResponse> {
    return apiClient
      .post<AnalyzeResponse>('/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60_000,
      })
      .then((r) => r.data);
  },

  async uploadAndPredict(imageFile: File): Promise<UploadAndPredictResult> {
    const formData = new FormData();
    formData.append('file', imageFile);

    const uploadResult = await this.analyze(formData);
    const prediction   = await this.predict({ image_url: uploadResult.cloudinary_url });

    return { cloudinary_url: uploadResult.cloudinary_url, prediction };
  },
};

export default apiClient;
