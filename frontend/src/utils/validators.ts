/**
 * utils/validators.ts
 * --------------------
 * Funciones de validación en cliente para formularios de Frotis AI.
 * Replica las reglas de validación del backend (Pydantic schemas).
 */

// ---------------------------------------------------------------------------
// Tipos de retorno
// ---------------------------------------------------------------------------

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

export interface PasswordValidationResult extends ValidationResult {
  strength?: 'weak' | 'medium' | 'strong';
}

export interface FormValidationResult {
  valid: boolean;
  errors: Record<string, string>;
  passwordStrength?: 'weak' | 'medium' | 'strong';
}

// ---------------------------------------------------------------------------
// Email
// ---------------------------------------------------------------------------

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function validateEmail(email: string): ValidationResult {
  if (!email?.trim()) {
    return { valid: false, error: 'El email es obligatorio.' };
  }
  if (!EMAIL_REGEX.test(email.trim())) {
    return { valid: false, error: 'Ingresa un email con formato válido.' };
  }
  if (email.length > 254) {
    return { valid: false, error: 'El email no puede superar 254 caracteres.' };
  }
  return { valid: true };
}

// ---------------------------------------------------------------------------
// Password
// ---------------------------------------------------------------------------

function calcStrength(password: string): 'weak' | 'medium' | 'strong' {
  let score = 0;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;
  return score >= 2 ? 'strong' : score === 1 ? 'medium' : 'weak';
}

export function validatePassword(password: string): PasswordValidationResult {
  if (!password) {
    return { valid: false, error: 'La contraseña es obligatoria.' };
  }
  if (password.length < 8) {
    return { valid: false, error: 'La contraseña debe tener al menos 8 caracteres.' };
  }
  if (password.length > 128) {
    return { valid: false, error: 'La contraseña no puede superar 128 caracteres.' };
  }
  if (!/[a-zA-Z]/.test(password)) {
    return { valid: false, error: 'La contraseña debe contener al menos una letra.' };
  }
  if (!/[0-9]/.test(password)) {
    return { valid: false, error: 'La contraseña debe contener al menos un número.' };
  }
  return { valid: true, strength: calcStrength(password) };
}

/** Calcula la fortaleza sin validar — útil para feedback en tiempo real */
export function getPasswordStrength(
  password: string
): 'weak' | 'medium' | 'strong' | null {
  if (!password || password.length < 8) return null;
  return calcStrength(password);
}

// ---------------------------------------------------------------------------
// URL de Cloudinary
// ---------------------------------------------------------------------------

export function validateCloudinaryUrl(url: string): ValidationResult {
  if (!url?.trim()) {
    return { valid: false, error: 'La URL de imagen es obligatoria.' };
  }
  try {
    const parsed = new URL(url.trim());
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return { valid: false, error: 'La URL debe usar protocolo HTTP/HTTPS.' };
    }
    if (!parsed.hostname.includes('cloudinary.com')) {
      return { valid: false, error: 'Solo se aceptan URLs de Cloudinary.' };
    }
  } catch {
    return { valid: false, error: 'URL con formato inválido.' };
  }
  return { valid: true };
}

// ---------------------------------------------------------------------------
// Archivo de imagen
// ---------------------------------------------------------------------------

const ACCEPTED_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/tiff',
  'image/bmp',
] as const;

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

export function validateImageFile(file: File | null | undefined): ValidationResult {
  if (!file) {
    return { valid: false, error: 'Selecciona un archivo de imagen.' };
  }
  if (!ACCEPTED_TYPES.includes(file.type as (typeof ACCEPTED_TYPES)[number])) {
    return { valid: false, error: 'Formato no soportado. Usa JPEG, PNG, TIFF o BMP.' };
  }
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `El archivo supera el límite de ${MAX_FILE_SIZE / 1024 / 1024} MB.`,
    };
  }
  return { valid: true };
}

// ---------------------------------------------------------------------------
// Sanitización básica
// ---------------------------------------------------------------------------

export function sanitizeString(str: unknown): string {
  if (!str || typeof str !== 'string') return '';
  return str
    .trim()
    .replace(/[<>'"]/g, '')
    .slice(0, 1000);
}

// ---------------------------------------------------------------------------
// Formularios completos
// ---------------------------------------------------------------------------

export interface RegistrationFormData {
  email: string;
  password: string;
  confirmPassword: string;
}

export function validateRegistrationForm(
  data: RegistrationFormData
): FormValidationResult {
  const errors: Record<string, string> = {};

  const emailResult = validateEmail(data.email);
  if (!emailResult.valid && emailResult.error) errors.email = emailResult.error;

  const passwordResult = validatePassword(data.password);
  if (!passwordResult.valid && passwordResult.error) {
    errors.password = passwordResult.error;
  }

  if (!data.confirmPassword) {
    errors.confirmPassword = 'Confirma tu contraseña.';
  } else if (data.password !== data.confirmPassword) {
    errors.confirmPassword = 'Las contraseñas no coinciden.';
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
    passwordStrength: passwordResult.strength,
  };
}

export interface LoginFormData {
  email: string;
  password: string;
}

export function validateLoginForm(data: LoginFormData): FormValidationResult {
  const errors: Record<string, string> = {};

  const emailResult = validateEmail(data.email);
  if (!emailResult.valid && emailResult.error) errors.email = emailResult.error;

  if (!data.password?.trim()) {
    errors.password = 'La contraseña es obligatoria.';
  }

  return { valid: Object.keys(errors).length === 0, errors };
}
