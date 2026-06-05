/**
 * components/ResultsPanel/ResultsPanel.tsx
 * ------------------------------------------
 * Panel lateral de resultados del análisis de frotis.
 */

import type { PredictResponse, ClaseDistribucion } from '../../types/api';
import './ResultsPanel.css';

// ---------------------------------------------------------------------------
// Paleta (consistente con ImageViewer)
// ---------------------------------------------------------------------------

const CELL_COLORS: readonly string[] = [
  '#f37421', '#54643c', '#17ab9c', '#c0760a', '#3d7a60',
  '#7c5cbf', '#bf5c5c', '#5c8ebf', '#bf9c5c', '#5cbf7c',
] as const;

function getColorForClass(className: string): string {
  let hash = 0;
  for (const ch of className) hash = (hash * 31 + ch.charCodeAt(0)) % CELL_COLORS.length;
  return CELL_COLORS[hash] ?? '#f37421';
}

// ---------------------------------------------------------------------------
// Insight automático
// ---------------------------------------------------------------------------

function generateInsight(distribution: Record<string, ClaseDistribucion>): string | null {
  const entries = Object.entries(distribution).sort(
    (a, b) => b[1].porcentaje - a[1].porcentaje
  );
  if (entries.length === 0) return null;

  const [topClass, topData] = entries[0];
  if (topData.porcentaje > 70) {
    return `Predominancia marcada de ${topClass} (${topData.porcentaje}%). Evaluación clínica recomendada.`;
  }
  if (topData.porcentaje > 50) {
    return `${topClass} es la clase celular más frecuente (${topData.porcentaje}% del total).`;
  }
  return `Distribución variada — ${entries.length} tipos celulares detectados.`;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ResultsPanelProps {
  prediction?: PredictResponse | null;
  isLoading?:  boolean;
  imageUrl?:   string | null;
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export default function ResultsPanel({
  prediction = null,
  isLoading  = false,
  imageUrl   = null,
}: ResultsPanelProps) {

  // Estado: cargando
  if (isLoading) {
    return (
      <aside className="results-panel results-panel-loading" aria-label="Resultados del análisis cargando">
        <div className="results-panel-header">
          <h2 className="results-panel-title">Analizando…</h2>
        </div>
        <div className="results-loading-area">
          <div className="spinner spinner-lg" aria-label="Cargando resultados" />
          <p>El modelo está procesando la imagen…</p>
        </div>
      </aside>
    );
  }

  // Estado: vacío
  if (!prediction) {
    return (
      <aside className="results-panel results-panel-empty" aria-label="Panel de resultados vacío">
        <div className="results-panel-header">
          <h2 className="results-panel-title">Resultados</h2>
          <p className="results-panel-subtitle">El análisis aparecerá aquí</p>
        </div>
        <div className="results-empty-state">
          <span className="results-empty-icon" aria-hidden="true">🧬</span>
          <p>Sube una imagen de frotis y ejecuta el análisis para ver las detecciones y estadísticas.</p>
        </div>
      </aside>
    );
  }

  const { total_detecciones, distribucion, detecciones, analisis_id } = prediction;
  const insight    = generateInsight(distribucion);
  const sortedDist = Object.entries(distribucion).sort((a, b) => b[1].porcentaje - a[1].porcentaje);

  return (
    <aside className="results-panel animate-fade-in" aria-label="Resultados del análisis">

      {/* Header */}
      <div className="results-panel-header">
        <div className="results-status-badge">
          <span className="badge badge-success">
            <span className="badge-dot" />
            Completado
          </span>
          {analisis_id && (
            <span className="badge badge-neutral" title={`ID: ${analisis_id}`}>
              Guardado
            </span>
          )}
        </div>
        <h2 className="results-panel-title">Resultados</h2>
      </div>

      {/* Conteo total — tipografía serif grande */}
      <div className="results-count-card">
        <p className="results-count-label">Total detectado</p>
        <p className="results-count-value" aria-label={`${total_detecciones} leucocitos detectados`}>
          {total_detecciones}
        </p>
        <p className="results-count-unit">leucocitos</p>
      </div>

      {/* Insight en teal */}
      {insight && (
        <div className="results-insight" role="note" aria-label="Observación automática">
          <span className="results-insight-icon" aria-hidden="true">💡</span>
          <p>{insight}</p>
          <p className="results-insight-disclaimer">Orientativo — no reemplaza diagnóstico médico</p>
        </div>
      )}

      {/* Distribución */}
      {sortedDist.length > 0 && (
        <section className="results-section" aria-labelledby="dist-heading">
          <h3 className="results-section-title" id="dist-heading">Distribución celular</h3>
          <div className="results-distribution">
            {sortedDist.map(([className, data]) => {
              const color = getColorForClass(className);
              return (
                <div key={className} className="dist-item">
                  <div className="dist-item-header">
                    <span className="dist-item-name">
                      <span className="dist-item-dot" style={{ background: color }} aria-hidden="true" />
                      {className}
                    </span>
                    <span className="dist-item-stats">
                      <strong>{data.cantidad}</strong>
                      <span className="dist-item-pct">{data.porcentaje}%</span>
                    </span>
                  </div>
                  <div
                    className="progress-bar"
                    role="progressbar"
                    aria-valuenow={data.porcentaje}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`${className}: ${data.porcentaje}%`}
                  >
                    <div
                      className="progress-fill"
                      style={{ width: `${data.porcentaje}%`, background: color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Detecciones individuales */}
      {detecciones.length > 0 && (
        <section className="results-section" aria-labelledby="det-heading">
          <h3 className="results-section-title" id="det-heading">
            Detecciones individuales
            <span className="results-count-badge">{detecciones.length}</span>
          </h3>
          <div className="results-detections-list">
            {detecciones.slice(0, 20).map((det, idx) => {
              const color = getColorForClass(det.clase);
              const pct   = Math.round(det.confianza * 100);
              return (
                <div key={idx} className="detection-item">
                  <span className="detection-dot" style={{ background: color }} aria-hidden="true" />
                  <span className="detection-class">{det.clase}</span>
                  <span className="detection-confidence" style={{ color }} aria-label={`Confianza: ${pct}%`}>
                    {pct}%
                  </span>
                </div>
              );
            })}
            {detecciones.length > 20 && (
              <p className="detections-more">+ {detecciones.length - 20} detecciones más</p>
            )}
          </div>
        </section>
      )}

      {/* Metadata */}
      {imageUrl && (
        <section className="results-section results-meta" aria-labelledby="meta-heading">
          <h3 className="results-section-title" id="meta-heading">Metadata</h3>
          <div className="results-meta-grid">
            <div className="meta-item">
              <span className="meta-label">Imagen</span>
              <a className="meta-value meta-link" href={imageUrl} target="_blank" rel="noopener noreferrer">
                Ver original ↗
              </a>
            </div>
            {analisis_id && (
              <div className="meta-item">
                <span className="meta-label">ID análisis</span>
                <code className="meta-value" title={analisis_id}>
                  {analisis_id.slice(0, 8)}…
                </code>
              </div>
            )}
          </div>
        </section>
      )}
    </aside>
  );
}
