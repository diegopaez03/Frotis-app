/**
 * components/FeedbackPanel/FeedbackPanel.tsx
 * -------------------------------------------
 * Panel lateral para listar, eliminar y enviar las correcciones
 * realizadas por el bioquímico sobre el análisis actual.
 */

import type { FeedbackItem } from '../../types/api';
import './FeedbackPanel.css';

interface FeedbackPanelProps {
  feedbacks: FeedbackItem[];
  onRemoveFeedback: (index: number) => void;
  onSubmit: () => void;
  onCancel: () => void;
  isSubmitting?: boolean;
  saveError?: string | null;
}

export default function FeedbackPanel({
  feedbacks,
  onRemoveFeedback,
  onSubmit,
  onCancel,
  isSubmitting = false,
  saveError = null,
}: FeedbackPanelProps) {
  return (
    <aside className="feedback-panel animate-fade-in" aria-label="Panel de correcciones">
      <div className="feedback-panel-header">
        <h2 className="feedback-panel-title">Modo Corrección</h2>
        <p className="feedback-panel-subtitle">Gestiona las correcciones aplicadas</p>
      </div>

      {feedbacks.length === 0 ? (
        <div className="feedback-empty-state">
          <span className="feedback-empty-icon" aria-hidden="true">✏️</span>
          <p className="feedback-empty-text">
            No hay correcciones pendientes.
          </p>
          <p className="feedback-empty-instructions">
            Haz clic en una célula existente para corregir su clase o marcarla como falso positivo, o dibuja un cuadro en la imagen para agregar una omitida.
          </p>
        </div>
      ) : (
        <div className="feedback-list-section">
          <h3 className="feedback-list-title">
            Correcciones pendientes ({feedbacks.length})
          </h3>
          <div className="feedback-items-list">
            {feedbacks.map((item, idx) => {
              let badgeText = '';
              let badgeClass = '';
              let descText = '';

              switch (item.tipoCorreccion) {
                case 'FALSO_POSITIVO':
                  badgeText = 'Falso Positivo';
                  badgeClass = 'badge-feedback-error';
                  descText = 'Se descartará esta detección del análisis.';
                  break;
                case 'CAMBIO_CLASE':
                  badgeText = 'Clase Corregida';
                  badgeClass = 'badge-feedback-warning';
                  descText = `Cambiar clase a: ${item.claseCorregida}`;
                  break;
                case 'NUEVA_DETECCION':
                  badgeText = 'Nueva Detección';
                  badgeClass = 'badge-feedback-success';
                  descText = `Agregar célula: ${item.claseCorregida}`;
                  break;
              }

              return (
                <div key={idx} className="feedback-list-card">
                  <div className="feedback-card-header">
                    <span className={`badge-feedback ${badgeClass}`}>
                      {badgeText}
                    </span>
                    <button
                      className="btn-feedback-delete"
                      onClick={() => onRemoveFeedback(idx)}
                      title="Eliminar esta corrección"
                      aria-label="Eliminar corrección"
                    >
                      ×
                    </button>
                  </div>
                  <div className="feedback-card-body">
                    <p className="feedback-card-desc">{descText}</p>
                    {item.bbox_corregido && (
                      <span className="feedback-card-coords">
                        Caja: [{item.bbox_corregido.map(Math.round).join(', ')}]
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Acciones principales */}
      <div className="feedback-panel-footer">
        {saveError && (
          <div className="feedback-error-alert" role="alert">
            ⚠️ {saveError}
          </div>
        )}
        <button
          className="btn btn-primary w-full"
          onClick={onSubmit}
          disabled={feedbacks.length === 0 || isSubmitting}
        >
          {isSubmitting ? (
            <span className="feedback-spinner-wrapper">
              <span className="spinner spinner-xs" aria-hidden="true" />
              Guardando...
            </span>
          ) : (
            'Guardar cambios'
          )}
        </button>
        <button
          className="btn btn-ghost w-full"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          Cancelar
        </button>
      </div>
    </aside>
  );
}
