/**
 * pages/WorkspacePage/WorkspacePage.tsx
 * ---------------------------------------
 * Vista de análisis activo — workspace médico principal.
 */

import {
  useState,
  useCallback,
  useRef,
  DragEvent,
  ChangeEvent,
  FormEvent,
} from 'react';
import { useNavigate } from 'react-router-dom';
import ImageViewer from '../../components/ImageViewer/ImageViewer';
import ResultsPanel from '../../components/ResultsPanel/ResultsPanel';
import { analysisAPI } from '../../services/api';
import { validateImageFile } from '../../utils/validators';
import { useToast } from '../../contexts/ToastContext';
import { useAuth } from '../../contexts/AuthContext';
import type { PredictResponse, ApiError } from '../../types/api';
import './WorkspacePage.css';

// ---------------------------------------------------------------------------
// Subcomponente: Drop zone
// ---------------------------------------------------------------------------

interface DropZoneProps {
  onFile: (file: File) => void;
  isDisabled: boolean;
}

function DropZone({ onFile, isDisabled }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(
    (file: File): void => {
      const { valid, error } = validateImageFile(file);
      if (!valid) { alert(error); return; }
      onFile(file);
    },
    [onFile]
  );

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>): void => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleChange = (e: ChangeEvent<HTMLInputElement>): void => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    e.target.value = '';
  };

  return (
    <div
      className={`dropzone${isDragOver ? ' dropzone-active' : ''}${isDisabled ? ' dropzone-disabled' : ''}`}
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onClick={() => !isDisabled && inputRef.current?.click()}
      role="button"
      tabIndex={isDisabled ? -1 : 0}
      aria-label="Zona de carga de imagen — haz clic o arrastra un archivo"
      onKeyDown={(e) => e.key === 'Enter' && !isDisabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        id="workspace-file-input"
        type="file"
        accept=".jpg,.jpeg,.png,.tif,.tiff,.bmp"
        style={{ display: 'none' }}
        onChange={handleChange}
        aria-hidden="true"
        disabled={isDisabled}
      />
      <span className="dropzone-icon" aria-hidden="true">📂</span>
      <p className="dropzone-title">Arrastra tu imagen aquí</p>
      <p className="dropzone-subtitle">
        o <span className="dropzone-link">selecciona un archivo</span>
      </p>
      <p className="dropzone-formats">JPEG, PNG, TIFF, BMP · Máx. 20 MB</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Subcomponente: input URL de Cloudinary
// ---------------------------------------------------------------------------

interface CloudinaryUrlInputProps {
  onUrl: (url: string) => void;
  isDisabled: boolean;
}

function CloudinaryUrlInput({ onUrl, isDisabled }: CloudinaryUrlInputProps) {
  const [value, setValue] = useState('');
  const [error, setError] = useState('');

  function handleSubmit(e: FormEvent<HTMLFormElement>): void {
    e.preventDefault();
    if (!value.trim()) { setError('Ingresa una URL.'); return; }
    setError('');
    onUrl(value.trim());
  }

  return (
    <form className="cloudinary-url-form" onSubmit={handleSubmit} noValidate>
      <div className="form-group">
        <label className="form-label" htmlFor="cloudinary-url-input">
          URL de Cloudinary
        </label>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <input
            id="cloudinary-url-input"
            type="url"
            className={`form-input flex-1${error ? ' input-error' : ''}`}
            placeholder="https://res.cloudinary.com/…"
            value={value}
            onChange={(e) => { setValue(e.target.value); setError(''); }}
            disabled={isDisabled}
            aria-label="URL de imagen en Cloudinary"
            aria-invalid={!!error}
          />
          <button
            type="submit"
            id="cloudinary-url-submit"
            className="btn btn-tertiary btn-sm"
            disabled={isDisabled || !value.trim()}
            aria-label="Analizar URL de imagen"
          >
            Analizar
          </button>
        </div>
        {error && <span className="form-error">{error}</span>}
      </div>
    </form>
  );
}

type UploadMode = 'file' | 'url';

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

export default function WorkspacePage() {
  const { isAuthenticated } = useAuth();
  const { showToast }       = useToast();
  const navigate            = useNavigate();

  const [imageFile,     setImageFile]     = useState<File | null>(null);
  const [imagePreview,  setImagePreview]  = useState<string | null>(null);
  const [cloudinaryUrl, setCloudinaryUrl] = useState<string | null>(null);
  const [prediction,    setPrediction]    = useState<PredictResponse | null>(null);
  const [isUploading,   setIsUploading]   = useState(false);
  const [isPredicting,  setIsPredicting]  = useState(false);
  const [uploadMode,    setUploadMode]    = useState<UploadMode>('file');
  const [showBboxes,    setShowBboxes]    = useState(true);

  // ------------------------------------------------------------------
  // Manejar selección de archivo
  // ------------------------------------------------------------------
  const handleFileSelected = useCallback((file: File): void => {
    setImageFile(file);
    setPrediction(null);
    setCloudinaryUrl(null);
    const objectUrl = URL.createObjectURL(file);
    setImagePreview(objectUrl);
  }, []);

  // ------------------------------------------------------------------
  // Manejar URL directa
  // ------------------------------------------------------------------
  const handleDirectUrl = useCallback((url: string): void => {
    setPrediction(null);
    setImageFile(null);
    setImagePreview(url);
    setCloudinaryUrl(url);
  }, []);

  // ------------------------------------------------------------------
  // Ejecutar análisis
  // ------------------------------------------------------------------
  async function runAnalysis(): Promise<void> {
    if (!imageFile && !cloudinaryUrl) return;

    try {
      if (imageFile) {
        setIsUploading(true);
        try {
          const result = await analysisAPI.uploadAndPredict(imageFile);
          setCloudinaryUrl(result.cloudinary_url);
          setImagePreview(result.cloudinary_url);
          setPrediction(result.prediction);
          showToast('success', 'Análisis completado', `${result.prediction.total_detecciones} leucocitos detectados.`);
          if (isAuthenticated && result.prediction.analisis_id) {
            navigate(`/analysis/${result.prediction.analisis_id}`);
          }
        } finally {
          setIsUploading(false);
        }
        return;
      }

      if (cloudinaryUrl) {
        setIsPredicting(true);
        try {
          const result = await analysisAPI.predict({ image_url: cloudinaryUrl });
          setPrediction(result);
          showToast('success', 'Análisis completado', `${result.total_detecciones} leucocitos detectados en la imagen.`);
          if (isAuthenticated && result.analisis_id) {
            navigate(`/analysis/${result.analisis_id}`);
          }
        } finally {
          setIsPredicting(false);
        }
      }
    } catch (err) {
      const msg = (err as Partial<ApiError>).message ?? 'Error durante el análisis.';
      showToast('error', 'Error de análisis', msg);
      setIsUploading(false);
      setIsPredicting(false);
    }
  }

  // ------------------------------------------------------------------
  // Resetear workspace
  // ------------------------------------------------------------------
  function resetWorkspace(): void {
    if (imagePreview?.startsWith('blob:')) URL.revokeObjectURL(imagePreview);
    setImageFile(null);
    setImagePreview(null);
    setCloudinaryUrl(null);
    setPrediction(null);
  }

  const isProcessing = isUploading || isPredicting;
  const hasImage = imagePreview !== null;
  const canAnalyze = hasImage && !isProcessing && prediction === null;
  const activeImageUrl = prediction ? (cloudinaryUrl ?? imagePreview) : imagePreview;

  return (
    <div className="workspace-page">
      {/* Top bar */}
      <div className="workspace-topbar">
        <div className="workspace-topbar-left">
          <h1 className="workspace-title">Workspace de análisis</h1>
          {!isAuthenticated && (
            <span className="badge badge-warning">
              <span className="badge-dot" />
              Modo anónimo — los resultados no se guardarán
            </span>
          )}
        </div>
        <div className="workspace-topbar-right">
          {hasImage && (
            <>
              <label className="workspace-toggle-label" htmlFor="toggle-bboxes">
                <input
                  id="toggle-bboxes"
                  type="checkbox"
                  className="workspace-toggle"
                  checked={showBboxes}
                  onChange={(e) => setShowBboxes(e.target.checked)}
                  aria-label="Mostrar detecciones en imagen"
                />
                <span>Mostrar detecciones</span>
              </label>
              <button
                id="workspace-reset-btn"
                className="btn btn-ghost btn-sm"
                onClick={resetWorkspace}
                aria-label="Limpiar workspace"
              >
                ✕ Limpiar
              </button>
            </>
          )}
        </div>
      </div>

      {/* Split layout */}
      <div className="workspace-main">
        {/* Viewer — 65% */}
        <div className="workspace-viewer-area">
          <ImageViewer
            imageUrl={activeImageUrl}
            detections={prediction?.detecciones ?? []}
            showBboxes={showBboxes}
            className="workspace-viewer"
          />
        </div>

        {/* Controls + Results — 35% */}
        <div className="workspace-sidebar">
          {!prediction && (
            <div className="workspace-upload-panel">
              <div className="workspace-upload-header">
                <h2 className="workspace-upload-title">Nueva imagen</h2>
                <div className="workspace-mode-tabs" role="tablist">
                  {(['file', 'url'] as UploadMode[]).map((m) => (
                    <button
                      key={m}
                      id={`mode-tab-${m}`}
                      role="tab"
                      aria-selected={uploadMode === m}
                      className={`workspace-mode-tab${uploadMode === m ? ' active' : ''}`}
                      onClick={() => setUploadMode(m)}
                    >
                      {m === 'file' ? 'Archivo' : 'URL'}
                    </button>
                  ))}
                </div>
              </div>

              {uploadMode === 'file' ? (
                <DropZone onFile={handleFileSelected} isDisabled={isProcessing} />
              ) : (
                <CloudinaryUrlInput onUrl={handleDirectUrl} isDisabled={isProcessing} />
              )}

              {imageFile && (
                <div className="workspace-file-info">
                  <span className="workspace-file-name" title={imageFile.name}>
                    📄 {imageFile.name}
                  </span>
                  <span className="workspace-file-size">
                    {(imageFile.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </div>
              )}

              {hasImage && (
                <button
                  id="workspace-analyze-btn"
                  className={`btn btn-primary btn-full${isProcessing ? ' btn-loading' : ''}`}
                  onClick={() => void runAnalysis()}
                  disabled={!canAnalyze}
                  aria-label="Iniciar análisis de frotis"
                >
                  {isUploading ? (
                    <><span className="btn-spinner" aria-hidden="true" /> <span className="btn-text">Subiendo imagen…</span></>
                  ) : isPredicting ? (
                    <><span className="btn-spinner" aria-hidden="true" /> <span className="btn-text">Analizando frotis…</span></>
                  ) : (
                    <><span aria-hidden="true">⚡</span> Iniciar análisis</>
                  )}
                </button>
              )}

              {!isAuthenticated && hasImage && (
                <p className="workspace-auth-note">
                  ℹ️ Inicia sesión para guardar resultados en tu historial
                </p>
              )}
            </div>
          )}

          <ResultsPanel
            prediction={prediction}
            isLoading={isProcessing}
            imageUrl={cloudinaryUrl ?? imagePreview}
          />

          {prediction && (
            <div className="workspace-new-analysis">
              <button
                id="workspace-new-btn"
                className="btn btn-outline btn-full"
                onClick={resetWorkspace}
              >
                ← Nuevo análisis
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
