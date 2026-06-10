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
import FeedbackPanel from '../../components/FeedbackPanel/FeedbackPanel';
import { analysisAPI } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import type {
  AnalysisListItem,
  PredictResponse,
  ApiError,
  FeedbackItem,
  DeteccionItem,
} from '../../types/api';
import './AnalysisDetailPage.css';

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const CELL_CLASSES = ['Neutrófilo', 'Linfocito', 'Monocito', 'Eosinófilo', 'Basófilo'];

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
  const { showToast } = useToast();

  const [analysis,   setAnalysis]   = useState<AnalysisListItem | null>(null);
  const [prediction, setPrediction] = useState<PredictResponse  | null>(null);
  const [isLoading,  setIsLoading]  = useState(true);
  const [loadError,  setLoadError]  = useState<string | null>(null);
  const [showBboxes, setShowBboxes] = useState(true);

  // Deletion states
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Feedback states
  const [isFeedbackMode, setIsFeedbackMode] = useState(false);
  const [drawTool, setDrawTool] = useState<'pan' | 'draw'>('pan');
  const [pendingFeedbacks, setPendingFeedbacks] = useState<FeedbackItem[]>([]);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Modals state
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedDeteccion, setSelectedDeteccion] = useState<DeteccionItem | null>(null);
  const [correctedClass, setCorrectedClass] = useState<string>('Neutrófilo');

  const [showNewDeteccionModal, setShowNewDeteccionModal] = useState(false);
  const [drawnBbox, setDrawnBbox] = useState<[number, number, number, number] | null>(null);
  const [newDeteccionClass, setNewDeteccionClass] = useState<string>('Neutrófilo');

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
  // Handlers para Feedback
  // ------------------------------------------------------------------
  const handleSelectDetection = (det: DeteccionItem) => {
    setSelectedDeteccion(det);
    const existingFb = pendingFeedbacks.find(
      (f) => f.deteccion_id === det.id && f.tipoCorreccion === 'CAMBIO_CLASE'
    );
    setCorrectedClass(existingFb?.claseCorregida || det.clase);
    setShowEditModal(true);
  };

  const handleDrawBbox = (bbox: [number, number, number, number]) => {
    setDrawnBbox(bbox);
    setNewDeteccionClass('Neutrófilo');
    setShowNewDeteccionModal(true);
  };

  const handleSaveClassChange = () => {
    if (!selectedDeteccion) return;
    const newFeedbacks = pendingFeedbacks.filter((f) => f.deteccion_id !== selectedDeteccion.id);
    newFeedbacks.push({
      deteccion_id: selectedDeteccion.id,
      tipoCorreccion: 'CAMBIO_CLASE',
      claseCorregida: correctedClass,
    });
    setPendingFeedbacks(newFeedbacks);
    setShowEditModal(false);
    setSelectedDeteccion(null);
  };

  const handleMarkAsFalsePositive = () => {
    if (!selectedDeteccion) return;
    const newFeedbacks = pendingFeedbacks.filter((f) => f.deteccion_id !== selectedDeteccion.id);
    newFeedbacks.push({
      deteccion_id: selectedDeteccion.id,
      tipoCorreccion: 'FALSO_POSITIVO',
    });
    setPendingFeedbacks(newFeedbacks);
    setShowEditModal(false);
    setSelectedDeteccion(null);
  };

  const handleSaveNewDeteccion = () => {
    if (!drawnBbox) return;
    setPendingFeedbacks([
      ...pendingFeedbacks,
      {
        deteccion_id: null,
        tipoCorreccion: 'NUEVA_DETECCION',
        claseCorregida: newDeteccionClass,
        bbox_corregido: drawnBbox,
      },
    ]);
    setShowNewDeteccionModal(false);
    setDrawnBbox(null);
  };

  const handleRemoveFeedback = (index: number) => {
    setPendingFeedbacks(pendingFeedbacks.filter((_, idx) => idx !== index));
  };

  const handleCancelFeedback = () => {
    setPendingFeedbacks([]);
    setIsFeedbackMode(false);
    setDrawTool('pan');
    setSaveError(null);
  };

  const handleSubmitFeedback = async () => {
    if (!id || pendingFeedbacks.length === 0) return;
    setIsSavingFeedback(true);
    setSaveError(null);
    try {
      await analysisAPI.submitFeedback(id, { feedbacks: pendingFeedbacks });
      // Recargar datos actualizados
      const updatedData = await analysisAPI.getById(id);
      setAnalysis(updatedData);
      setPrediction(itemToPrediction(updatedData));
      setPendingFeedbacks([]);
      setIsFeedbackMode(false);
      setDrawTool('pan');
    } catch (err) {
      const msg = (err as Partial<ApiError>).message ?? 'Error al guardar el feedback.';
      setSaveError(msg);
    } finally {
      setIsSavingFeedback(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setIsDeleting(true);
    try {
      await analysisAPI.delete(id);
      showToast('success', 'Éxito', 'Análisis eliminado correctamente.');
      setShowDeleteModal(false);
      void navigate('/dashboard');
    } catch (err) {
      const msg = (err as Partial<ApiError>).message ?? 'Error al eliminar el análisis.';
      showToast('error', 'Error al eliminar', msg);
    } finally {
      setIsDeleting(false);
    }
  };

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
          {analysis.estado === 'COMPLETED' && !isFeedbackMode && (
            <button
              id="detail-correct-btn"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setIsFeedbackMode(true);
                setShowBboxes(true); // Siempre mostrar bboxes en modo corrección
              }}
              aria-label="Corregir predicciones del análisis"
            >
              ✎ Corregir análisis
            </button>
          )}

          {!isFeedbackMode && (
            <button
              id="detail-delete-btn"
              className="btn btn-danger btn-sm"
              onClick={() => setShowDeleteModal(true)}
              aria-label="Eliminar análisis"
            >
              🗑️ Eliminar
            </button>
          )}

          {isFeedbackMode && (
            <div className="detail-draw-tools" role="group" aria-label="Herramientas de edición">
              <button
                className={`btn btn-sm ${drawTool === 'pan' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setDrawTool('pan')}
                title="Mover y Zoom"
              >
                🖐️ Mover
              </button>
              <button
                className={`btn btn-sm ${drawTool === 'draw' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setDrawTool('draw')}
                title="Dibujar detección manual"
              >
                ✏️ Dibujar
              </button>
            </div>
          )}

          <label className="workspace-toggle-label" htmlFor="detail-toggle-bboxes">
            <input
              id="detail-toggle-bboxes"
              type="checkbox"
              className="workspace-toggle"
              checked={showBboxes}
              onChange={(e) => setShowBboxes(e.target.checked)}
              aria-label="Mostrar detecciones en imagen"
              disabled={isFeedbackMode}
            />
            <span>Mostrar detecciones</span>
          </label>

          {!isFeedbackMode && (
            <button
              id="detail-new-analysis-btn"
              className="btn btn-primary btn-sm"
              onClick={() => void navigate('/workspace')}
              aria-label="Iniciar nuevo análisis"
            >
              ⊕ Nuevo análisis
            </button>
          )}
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
            feedbackMode={isFeedbackMode}
            drawTool={drawTool}
            onSelectDetection={handleSelectDetection}
            onDrawBbox={handleDrawBbox}
            pendingFeedbacks={pendingFeedbacks}
          />
        </div>

        {/* Panel lateral: Resultados u Hoja de corrección */}
        <div className="detail-panel-area">
          {isFeedbackMode ? (
            <FeedbackPanel
              feedbacks={pendingFeedbacks}
              onRemoveFeedback={handleRemoveFeedback}
              onSubmit={handleSubmitFeedback}
              onCancel={handleCancelFeedback}
              isSubmitting={isSavingFeedback}
              saveError={saveError}
            />
          ) : (
            <ResultsPanel
              prediction={prediction}
              isLoading={false}
              imageUrl={analysis.imagen_url}
            />
          )}
        </div>
      </div>

      {/* MODALES DE CORRECCIÓN */}
      
      {/* Modal: Editar/Corregir detección existente */}
      {showEditModal && selectedDeteccion && (
        <div className="detail-modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="detail-modal-header">
              <h3 className="detail-modal-title">Corregir Célula</h3>
              <p className="detail-modal-id">ID: {selectedDeteccion.id?.slice(0, 8)}...</p>
            </div>
            <div className="detail-modal-body">
              <p className="detail-modal-info">
                Detección original clasificada como <strong>{selectedDeteccion.clase}</strong> con <strong>{Math.round(selectedDeteccion.confianza * 100)}%</strong> de confianza.
              </p>
              
              <div className="detail-modal-field">
                <label htmlFor="modal-change-class-select">Cambiar clase celular:</label>
                <select
                  id="modal-change-class-select"
                  value={correctedClass}
                  onChange={(e) => setCorrectedClass(e.target.value)}
                  className="select-input"
                >
                  {CELL_CLASSES.map((cls) => (
                    <option key={cls} value={cls}>
                      {cls}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="detail-modal-footer">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setShowEditModal(false)}
              >
                Cancelar
              </button>
              <button
                className="btn btn-error btn-sm"
                onClick={handleMarkAsFalsePositive}
              >
                Falso Positivo
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSaveClassChange}
              >
                Aplicar cambio
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Agregar nueva detección manual */}
      {showNewDeteccionModal && drawnBbox && (
        <div className="detail-modal-overlay" onClick={() => setShowNewDeteccionModal(false)}>
          <div className="detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="detail-modal-header">
              <h3 className="detail-modal-title">Nueva Detección</h3>
              <p className="detail-modal-id">Coordenadas: [{drawnBbox.map(Math.round).join(', ')}]</p>
            </div>
            <div className="detail-modal-body">
              <p className="detail-modal-info">
                Selecciona la clase celular para el cuadro delimitador dibujado manualmente.
              </p>
              
              <div className="detail-modal-field">
                <label htmlFor="modal-new-class-select">Tipo celular:</label>
                <select
                  id="modal-new-class-select"
                  value={newDeteccionClass}
                  onChange={(e) => setNewDeteccionClass(e.target.value)}
                  className="select-input"
                >
                  {CELL_CLASSES.map((cls) => (
                    <option key={cls} value={cls}>
                      {cls}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="detail-modal-footer">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  setShowNewDeteccionModal(false);
                  setDrawnBbox(null);
                }}
              >
                Cancelar
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSaveNewDeteccion}
              >
                Agregar célula
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Confirmación de eliminación */}
      {showDeleteModal && (
        <div className="detail-modal-overlay" onClick={() => setShowDeleteModal(false)} id="delete-modal-overlay">
          <div className="detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="detail-modal-header">
              <h3 className="detail-modal-title">Eliminar Análisis</h3>
            </div>
            <div className="detail-modal-body">
              <p className="detail-modal-info">
                ¿Estás seguro de que deseas eliminar este análisis? Esta acción no se puede deshacer y lo ocultará de tu historial.
              </p>
            </div>
            <div className="detail-modal-footer">
              <button
                id="delete-modal-cancel-btn"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
              >
                Cancelar
              </button>
              <button
                id="delete-modal-confirm-btn"
                className="btn btn-danger btn-sm"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Eliminando...' : 'Confirmar Eliminación'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
