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
// Analysis list — GET /analysis response shape
// ---------------------------------------------------------------------------

/** Un ítem tal como lo devuelve GET /analysis */
export interface AnalysisListItem {
  id: string;
  imagen_url: string;
  estado: 'COMPLETED' | 'PENDING' | 'FAILED';
  fecha: string;
  total_detecciones: number;
  distribucion: Record<string, ClaseDistribucion>;
  detecciones: DeteccionItem[];
}

/**
 * Alias mantenido para compatibilidad con los componentes existentes.
 * Se deriva de AnalysisListItem; las clases_detectadas se extraen
 * de las keys de distribucion.
 */
export type AnalysisRecord = AnalysisListItem;

// ---------------------------------------------------------------------------
// Feedback — POST /analysis/{analysis_id}/feedback
// ---------------------------------------------------------------------------

export type TipoCorreccion = 'FALSO_POSITIVO' | 'CAMBIO_CLASE' | 'NUEVA_DETECCION';

export interface FeedbackItem {
  deteccion_id: string | null;
  tipoCorreccion: TipoCorreccion;
  claseCorregida?: string;
  bbox_corregido?: [number, number, number, number];
}

export interface FeedbackRequest {
  feedbacks: FeedbackItem[];
}

export interface FeedbackResponse {
  status: string;
  message: string;
}

