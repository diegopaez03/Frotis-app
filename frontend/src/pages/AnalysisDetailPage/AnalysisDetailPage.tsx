/**
 * pages/AnalysisDetailPage/AnalysisDetailPage.tsx
 * -------------------------------------------------
 * Vista de detalle de un análisis guardado.
 * Carga los datos desde GET /analysis/:id y muestra
 * el ImageViewer + ResultsPanel de solo lectura.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import ImageViewer  from '../../components/ImageViewer/ImageViewer';
import ResultsPanel from '../../components/ResultsPanel/ResultsPanel';
import { analysisAPI } from '../../services/api';
import type { AnalysisListItem, PredictResponse, ApiError } from '../../types/api';
import './AnalysisDetailPage.css';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function itemToPrediction(item: AnalysisListItem): PredictResponse {
  return {
    analisis_id:       item.id,
    total_detecciones: item.total_detecciones,
    distribucion:      item.distribucion,
    detecciones:       item.detecciones,
  };
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('es-AR', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export default function AnalysisDetailPage() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [analysis,   setAnalysis]   = useState<AnalysisListItem | null>(null);
  const [prediction, setPrediction] = useState<PredictResponse  | null>(null);
  const [isLoading,  setIsLoading]  = useState(true);
  const [loadError,  setLoadError]  = useState<string | null>(null);
  const [showBboxes, setShowBboxes] = useState(true);

  useEffect(() => {
    if (!id) {
      setLoadError('ID de análisis no proporcionado.');
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchDetail(): Promise<void> {
      setIsLoading(true);
      setLoadError(null);
      try {
        const data = await analysisAPI.getById(id);
        if (!cancelled) {
          setAnalysis(data);
          setPrediction(itemToPrediction(data));
        }
      } catch (err) {
        if (!cancelled) {
          const msg = (err as Partial<ApiError>).message ?? 'Error al cargar el análisis.';
          setLoadError(msg);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void fetchDetail();
    return () => { cancelled = true; };
  }, [id]);

  // ------------------------------------------------------------------
  // Estado: cargando
  // ------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="detail-page detail-loading">
        <div className="detail-loading-inner">
          <div className="spinner spinner-lg" aria-label="Cargando análisis" />
          <p className="detail-loading-text">Cargando análisis…</p>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Estado: error
  // ------------------------------------------------------------------
  if (loadError || !analysis) {
    return (
      <div className="detail-page detail-error">
        <div className="detail-error-inner">
          <span className="detail-error-icon" aria-hidden="true">⚠️</span>
          <h1 className="detail-error-title">No se pudo cargar el análisis</h1>
          <p className="detail-error-msg">{loadError ?? 'Análisis no encontrado.'}</p>
          <div className="detail-error-actions">
            <button
              className="btn btn-primary"
              onClick={() => void navigate('/dashboard')}
              id="detail-back-btn"
            >
              ← Volver al historial
            </button>
            {id && (
              <button
                className="btn btn-ghost"
                onClick={() => window.location.reload()}
                id="detail-retry-btn"
              >
                ⟳ Reintentar
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Vista principal
  // ------------------------------------------------------------------
  return (
    <div className="detail-page">
      {/* Top bar */}
      <div className="detail-topbar">
        <div className="detail-topbar-left">
          <Link
            to="/dashboard"
            className="detail-back-link"
            aria-label="Volver al historial de análisis"
          >
            ← Historial
          </Link>
          <div className="detail-topbar-info">
            <h1 className="detail-title">
              Análisis <span className="detail-id">#{analysis.id.slice(0, 8)}</span>
            </h1>
            <time className="detail-date" dateTime={analysis.fecha}>
              {formatDate(analysis.fecha)}
            </time>
          </div>
          <span className={`badge ${analysis.estado === 'COMPLETED' ? 'badge-success' : 'badge-warning'}`}>
            <span className="badge-dot" aria-hidden="true" />
            {analysis.estado}
          </span>
        </div>

        <div className="detail-topbar-right">
          <label className="workspace-toggle-label" htmlFor="detail-toggle-bboxes">
            <input
              id="detail-toggle-bboxes"
              type="checkbox"
              className="workspace-toggle"
              checked={showBboxes}
              onChange={(e) => setShowBboxes(e.target.checked)}
              aria-label="Mostrar detecciones en imagen"
            />
            <span>Mostrar detecciones</span>
          </label>
          <button
            id="detail-new-analysis-btn"
            className="btn btn-primary btn-sm"
            onClick={() => void navigate('/workspace')}
            aria-label="Iniciar nuevo análisis"
          >
            ⊕ Nuevo análisis
          </button>
        </div>
      </div>

      {/* Split layout: viewer 65% + panel 35% */}
      <div className="detail-main">
        {/* Viewer */}
        <div className="detail-viewer-area">
          <ImageViewer
            imageUrl={analysis.imagen_url}
            detections={analysis.detecciones}
            showBboxes={showBboxes}
            className="detail-viewer"
          />
        </div>

        {/* Results panel — read-only */}
        <div className="detail-panel-area">
          <ResultsPanel
            prediction={prediction}
            isLoading={false}
            imageUrl={analysis.imagen_url}
          />
        </div>
      </div>
    </div>
  );
}
