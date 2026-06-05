/**
 * types/api.ts
 * ------------
 * Tipos TypeScript para las respuestas y requests de la API de Frotis AI.
 * Espejo de los schemas Pydantic del backend.
 */

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface UserCreate {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  id: string;
  email: string;
  fechaCreacion: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
}

// ---------------------------------------------------------------------------
// Analysis / Prediction
// ---------------------------------------------------------------------------

export interface PredictRequest {
  image_url: string;
}

export interface DeteccionItem {
  id: string | null;
  clase: string;
  confianza: number;
  /** [x_min, y_min, x_max, y_max] */
  bbox: [number, number, number, number];
}

export interface ClaseDistribucion {
  cantidad: number;
  porcentaje: number;
}

export interface PredictResponse {
  analisis_id: string | null;
  total_detecciones: number;
  distribucion: Record<string, ClaseDistribucion>;
  detecciones: DeteccionItem[];
}

export interface AnalyzeResponse {
  cloudinary_url: string;
}

export interface UploadAndPredictResult {
  cloudinary_url: string;
  prediction: PredictResponse;
}

// ---------------------------------------------------------------------------
// API Error shape (normalised by the axios interceptor)
// ---------------------------------------------------------------------------

export type ApiErrorType =
  | 'NETWORK_ERROR'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'VALIDATION_ERROR'
  | 'SERVER_ERROR'
  | 'CLIENT_ERROR';

export interface ApiError {
  type: ApiErrorType;
  message: string;
  status?: number;
  fields?: unknown;
  original?: unknown;
}

// ---------------------------------------------------------------------------
// Analysis card (dashboard mock shape)
// ---------------------------------------------------------------------------

export interface AnalysisRecord {
  id: string;
  analisis_id: string;
  imagen_url: string | null;
  estado: 'COMPLETED' | 'PENDING' | 'FAILED';
  total_detecciones: number;
  clases_detectadas: string[];
  fecha: string;
  tipo: string;
}
