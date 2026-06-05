/**
 * pages/LoginPage/LoginPage.tsx
 * ------------------------------
 * Pantalla de autenticación — Login y Registro.
 * Layout de dos columnas: panel visual (izquierda) + formulario (derecha).
 */

import { useState, ChangeEvent, FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import {
  validateLoginForm,
  validateRegistrationForm,
  getPasswordStrength,
  LoginFormData,
  RegistrationFormData,
} from '../../utils/validators';
import type { ApiError } from '../../types/api';
import './LoginPage.css';

// ---------------------------------------------------------------------------
// Indicador de fortaleza de contraseña
// ---------------------------------------------------------------------------

type StrengthLevel = 'weak' | 'medium' | 'strong';

interface PasswordStrengthBarProps {
  strength: StrengthLevel;
}

function PasswordStrengthBar({ strength }: PasswordStrengthBarProps) {
  const levels: Record<StrengthLevel, number> = { weak: 1, medium: 2, strong: 3 };
  const labels: Record<StrengthLevel, string> = { weak: 'Débil', medium: 'Media', strong: 'Fuerte' };
  const colors: Record<StrengthLevel, string> = {
    weak: 'var(--color-error)',
    medium: 'var(--color-warning)',
    strong: 'var(--color-success)',
  };
  const level = levels[strength];

  return (
    <div
      className="password-strength"
      aria-live="polite"
      aria-label={`Fortaleza de contraseña: ${labels[strength]}`}
    >
      <div className="strength-bars">
        {([1, 2, 3] as const).map((i) => (
          <div
            key={i}
            className="strength-bar"
            style={i <= level ? { background: colors[strength] } : {}}
          />
        ))}
      </div>
      <span className="strength-label" style={{ color: colors[strength] }}>
        {labels[strength]}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tipos del formulario
// ---------------------------------------------------------------------------

type AuthMode = 'login' | 'register';

interface FormState {
  email: string;
  password: string;
  confirmPassword: string;
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export default function LoginPage() {
  const [mode, setMode] = useState<AuthMode>('login');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState<StrengthLevel | null>(null);

  const [formData, setFormData] = useState<FormState>({
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { login, register } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ??
    '/dashboard';

  // ----- Handlers -----

  function handleChange(e: ChangeEvent<HTMLInputElement>): void {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }

    if (name === 'password' && mode === 'register') {
      setPasswordStrength(getPasswordStrength(value));
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();

    let isValid: boolean;
    let formErrors: Record<string, string>;

    if (mode === 'login') {
      const result = validateLoginForm(formData as LoginFormData);
      isValid = result.valid;
      formErrors = result.errors;
    } else {
      const result = validateRegistrationForm(formData as RegistrationFormData);
      isValid = result.valid;
      formErrors = result.errors;
      if (result.passwordStrength) setPasswordStrength(result.passwordStrength);
    }

    if (!isValid) {
      setErrors(formErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      if (mode === 'login') {
        await login({ email: formData.email, password: formData.password });
        showToast('success', '¡Bienvenido!', `Sesión iniciada como ${formData.email}`);
      } else {
        await register({ email: formData.email, password: formData.password });
        showToast('success', '¡Cuenta creada!', 'Tu cuenta ha sido creada y has iniciado sesión.');
      }
      void navigate(from, { replace: true });
    } catch (err) {
      const apiError = err as Partial<ApiError>;
      const msg = apiError.message ?? 'Error inesperado. Inténtalo de nuevo.';

      setErrors({
        general: mode === 'login'
          ? 'Credenciales incorrectas. Verifica email y contraseña.'
          : msg,
      });
      showToast('error', 'Error de autenticación', msg);
    } finally {
      setIsLoading(false);
    }
  }

  function switchMode(newMode: AuthMode): void {
    setMode(newMode);
    setErrors({});
    setFormData({ email: formData.email, password: '', confirmPassword: '' });
    setPasswordStrength(null);
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="login-page">
      {/* Panel izquierdo: visual */}
      <div className="login-visual" aria-hidden="true">
        <div className="login-visual-overlay" />
        <div className="login-visual-content">
          <div className="login-brand-logo">
            <svg width="40" height="40" viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="28" r="16" stroke="rgba(255,255,255,0.9)" strokeWidth="4" />
              <circle cx="32" cy="28" r="7" fill="rgba(255,255,255,0.7)" />
              <line x1="32" y1="12" x2="32" y2="6" stroke="rgba(255,255,255,0.9)" strokeWidth="3" strokeLinecap="round" />
              <line x1="32" y1="44" x2="32" y2="56" stroke="rgba(255,255,255,0.9)" strokeWidth="3" strokeLinecap="round" />
              <line x1="25" y1="52" x2="39" y2="52" stroke="rgba(255,255,255,0.9)" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="login-visual-title">Frotis AI</h1>
          <p className="login-visual-subtitle">
            Análisis automatizado de frotis sanguíneo mediante inteligencia artificial
            para personal médico especializado.
          </p>
          <div className="login-visual-features">
            {[
              { icon: '🔬', text: 'Detección de 10 tipos de leucocitos' },
              { icon: '⚡', text: 'Resultados analizados con YOLOv8n' },
            ].map(({ icon, text }) => (
              <div key={text} className="login-feature-item">
                <span>{icon}</span>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="login-visual-circles" aria-hidden="true">
          <div className="vc-1" /><div className="vc-2" /><div className="vc-3" />
          <div className="vc-4" /><div className="vc-5" />
        </div>
      </div>

      {/* Panel derecho: formulario */}
      <div className="login-form-panel">
        <div className="login-form-container">

          {/* Tabs */}
          <div className="login-tabs" role="tablist" aria-label="Modo de autenticación">
            {(['login', 'register'] as AuthMode[]).map((m) => (
              <button
                key={m}
                id={`tab-${m}`}
                role="tab"
                aria-selected={mode === m}
                className={`login-tab${mode === m ? ' login-tab-active' : ''}`}
                onClick={() => switchMode(m)}
              >
                {m === 'login' ? 'Iniciar sesión' : 'Registrarse'}
              </button>
            ))}
          </div>

          {/* Heading */}
          <div className="login-heading">
            <h2 className="login-title">
              {mode === 'login' ? 'Bienvenido de vuelta' : 'Crear cuenta'}
            </h2>
            <p className="login-subtitle">
              {mode === 'login'
                ? 'Ingresa tus credenciales para acceder al sistema'
                : 'Crea tu cuenta para comenzar a analizar frotis'}
            </p>
          </div>

          {/* Form */}
          <form
            className="login-form"
            onSubmit={(e) => void handleSubmit(e)}
            noValidate
            aria-label={mode === 'login' ? 'Formulario de inicio de sesión' : 'Formulario de registro'}
          >
            {errors.general && (
              <div className="form-error-banner" role="alert">
                <span aria-hidden="true">⚠</span> {errors.general}
              </div>
            )}

            {/* Email */}
            <div className="form-group">
              <label className="form-label" htmlFor="login-email">
                Email <span className="required" aria-hidden="true">*</span>
              </label>
              <input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                className={`form-input${errors.email ? ' input-error' : ''}`}
                placeholder="bioquimico@hospital.com"
                value={formData.email}
                onChange={handleChange}
                aria-invalid={!!errors.email}
                aria-describedby={errors.email ? 'email-error' : undefined}
                disabled={isLoading}
              />
              {errors.email && (
                <span id="email-error" className="form-error" role="alert">
                  <span aria-hidden="true">⚠</span> {errors.email}
                </span>
              )}
            </div>

            {/* Password */}
            <div className="form-group">
              <label className="form-label" htmlFor="login-password">
                Contraseña <span className="required" aria-hidden="true">*</span>
              </label>
              <div className="input-wrapper">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  className={`form-input${errors.password ? ' input-error' : ''}`}
                  placeholder="Mínimo 8 caracteres"
                  value={formData.password}
                  onChange={handleChange}
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="input-toggle-btn"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  id="toggle-password-visibility"
                >
                  {showPassword ? '🙉' : '🙈'}
                </button>
              </div>
              {errors.password && (
                <span id="password-error" className="form-error" role="alert">
                  <span aria-hidden="true">⚠</span> {errors.password}
                </span>
              )}
              {mode === 'register' && passwordStrength && (
                <PasswordStrengthBar strength={passwordStrength} />
              )}
            </div>

            {/* Confirm Password */}
            {mode === 'register' && (
              <div className="form-group">
                <label className="form-label" htmlFor="login-confirm-password">
                  Confirmar contraseña <span className="required" aria-hidden="true">*</span>
                </label>
                <div className="input-wrapper">
                  <input
                    id="login-confirm-password"
                    name="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    className={`form-input${errors.confirmPassword ? ' input-error' : ''}`}
                    placeholder="Repite la contraseña"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    aria-invalid={!!errors.confirmPassword}
                    aria-describedby={errors.confirmPassword ? 'confirm-password-error' : undefined}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="input-toggle-btn"
                    onClick={() => setShowConfirmPassword((v) => !v)}
                    aria-label={showConfirmPassword ? 'Ocultar confirmación' : 'Mostrar confirmación'}
                    id="toggle-confirm-password-visibility"
                  >
                    {showConfirmPassword ? '👁' : '🙈'}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <span id="confirm-password-error" className="form-error" role="alert">
                    <span aria-hidden="true">⚠</span> {errors.confirmPassword}
                  </span>
                )}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              id="login-submit-btn"
              className={`btn btn-primary btn-full btn-lg${isLoading ? ' btn-loading' : ''}`}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="btn-spinner" aria-hidden="true" />
                  <span className="btn-text">
                    {mode === 'login' ? 'Iniciando sesión…' : 'Creando cuenta…'}
                  </span>
                </>
              ) : (
                mode === 'login' ? 'Iniciar sesión' : 'Crear cuenta'
              )}
            </button>

            <p className="login-security-note" aria-label="Nota de seguridad">
              🔒 Datos protegidos
            </p>
          </form>

          <p className="login-switch">
            {mode === 'login' ? (
              <>¿No tienes cuenta?{' '}
                <button className="login-switch-btn" onClick={() => switchMode('register')} id="switch-to-register">
                  Regístrate aquí
                </button>
              </>
            ) : (
              <>¿Ya tienes cuenta?{' '}
                <button className="login-switch-btn" onClick={() => switchMode('login')} id="switch-to-login">
                  Inicia sesión
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
