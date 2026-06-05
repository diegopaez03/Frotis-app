/**
 * pages/DashboardPage/DashboardPage.tsx
 * ----------------------------------------
 * Vista principal del historial de análisis.
 * Carga datos reales desde GET /analysis (JWT inyectado automáticamente).
 */

import { useState, useEffect, ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import { analysisAPI } from '../../services/api';
import type { AnalysisListItem, ApiError } from '../../types/api';
import './DashboardPage.css';

// ---------------------------------------------------------------------------
// Helper: extrae clases detectadas desde el mapa de distribución
// ---------------------------------------------------------------------------

function getClasesFromDistribucion(
  distribucion: Record<string, { cantidad: number; porcentaje: number }>
): string[] {
  return Object.keys(distribucion);
}

// ---------------------------------------------------------------------------
// Subcomponente: tarjeta de análisis
// ---------------------------------------------------------------------------

interface AnalysisCardProps {
  analysis: AnalysisListItem;
  onClick:  () => void;
}

function AnalysisCard({ analysis, onClick }: AnalysisCardProps) {
  const date    = new Date(analysis.fecha);
  const dateStr = date.toLocaleDateString('es-AR', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
  const timeStr = date.toLocaleTimeString('es-AR', {
    hour: '2-digit', minute: '2-digit',
  });

  const clases = getClasesFromDistribucion(analysis.distribucion);

  return (
    <article
      className="analysis-card card card-interactive animate-fade-in"
      onClick={onClick}
      tabIndex={0}
      role="button"
      aria-label={`Análisis del ${dateStr}: ${analysis.total_detecciones} leucocitos detectados`}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      {/* Thumbnail */}
      <div className="analysis-card-thumb">
        {analysis.imagen_url ? (
          <img
            src={analysis.imagen_url}
            alt="Miniatura del frotis"
            className="analysis-card-thumb-img"
            loading="lazy"
          />
        ) : (
          <div className="analysis-card-thumb-content" aria-hidden="true">
            <span className="analysis-card-thumb-icon">🔬</span>
            <span className="analysis-card-thumb-count">{analysis.total_detecciones}</span>
            <span className="analysis-card-thumb-unit">células</span>
          </div>
        )}
        {/* Overlay con conteo cuando hay imagen */}
        {analysis.imagen_url && (
          <div className="analysis-card-thumb-overlay">
            <span className="analysis-card-thumb-count-overlay">
              {analysis.total_detecciones}
            </span>
            <span className="analysis-card-thumb-unit-overlay">células</span>
          </div>
        )}
      </div>

      <div className="analysis-card-body">
        <div className="analysis-card-badges">
          <span className={`badge ${analysis.estado === 'COMPLETED' ? 'badge-secondary' : 'badge-warning'}`}>
            <span className="badge-dot" aria-hidden="true" />
            {analysis.estado}
          </span>
        </div>

        <h3 className="analysis-card-title">
          Análisis #{analysis.id.slice(0, 8)}
        </h3>

        <div className="analysis-card-classes">
          {clases.slice(0, 3).map((cls) => (
            <span key={cls} className="chip">{cls}</span>
          ))}
          {clases.length > 3 && (
            <span className="chip">+{clases.length - 3}</span>
          )}
          {clases.length === 0 && (
            <span className="chip chip-muted">Sin clasificación</span>
          )}
        </div>

        <div className="analysis-card-footer">
          <time className="analysis-card-date" dateTime={analysis.fecha}>
            {dateStr} · {timeStr}
          </time>
          <span className="analysis-card-arrow" aria-hidden="true">→</span>
        </div>
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Estadísticas del encabezado
// ---------------------------------------------------------------------------

interface StatsRowProps {
  analyses: AnalysisListItem[];
}

function StatsRow({ analyses }: StatsRowProps) {
  const total      = analyses.length;
  const completed  = analyses.filter((a) => a.estado === 'COMPLETED').length;
  const totalCells = analyses.reduce((sum, a) => sum + a.total_detecciones, 0);

  return (
    <div className="dashboard-stats stagger-children">
      <div className="stat-card animate-fade-in">
        <p className="stat-card-label">Análisis realizados</p>
        <p className="stat-card-value">{total}</p>
        <p className="stat-card-sub">{completed} completados</p>
      </div>
      <div className="stat-card animate-fade-in">
        <p className="stat-card-label">Células detectadas</p>
        <p className="stat-card-value" style={{ color: 'var(--color-primary-dark)' }}>
          {totalCells.toLocaleString()}
        </p>
        <p className="stat-card-sub">Total acumulado</p>
      </div>
      <div className="stat-card animate-fade-in">
        <p className="stat-card-label">Promedio por análisis</p>
        <p className="stat-card-value" style={{ color: 'var(--color-tertiary)' }}>
          {total > 0 ? Math.round(totalCells / total) : 0}
        </p>
        <p className="stat-card-sub">leucocitos</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { user }      = useAuth();
  const navigate      = useNavigate();
  const { showToast } = useToast();

  const [analyses,    setAnalyses]    = useState<AnalysisListItem[]>([]);
  const [isLoading,   setIsLoading]   = useState(true);
  const [loadError,   setLoadError]   = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // ------------------------------------------------------------------
  // Cargar historial desde API
  // ------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    async function fetchAnalyses(): Promise<void> {
      setIsLoading(true);
      setLoadError(null);
      try {
        const data = await analysisAPI.getAll();
        if (!cancelled) {
          // Ordenar por fecha descendente (más reciente primero)
          const sorted = [...data].sort(
            (a, b) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime()
          );
          setAnalyses(sorted);
        }
      } catch (err) {
        if (!cancelled) {
          const msg = (err as Partial<ApiError>).message ?? 'Error al cargar el historial.';
          setLoadError(msg);
          showToast('error', 'Error al cargar historial', msg);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void fetchAnalyses();
    return () => { cancelled = true; };
  }, [showToast]);

  // ------------------------------------------------------------------
  // Filtrado por búsqueda
  // ------------------------------------------------------------------
  const filtered = analyses.filter((a) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const clases = getClasesFromDistribucion(a.distribucion);
    return (
      a.estado.toLowerCase().includes(q) ||
      clases.some((c) => c.toLowerCase().includes(q)) ||
      a.id.toLowerCase().includes(q)
    );
  });

  const userName = user?.email?.split('@')[0] ?? 'Usuario';

  return (
    <div className="dashboard-page">
      {/* Header */}
      <header className="dashboard-header">
        <div className="dashboard-header-text animate-fade-in-up">
          <h1 className="dashboard-greeting">
            Bienvenido, <span className="dashboard-greeting-name">{userName}</span>
          </h1>
          <p className="dashboard-subtitle">
            Historial de análisis de frotis sanguíneos
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => {
              setIsLoading(true);
              analysisAPI.getAll()
                .then((data) => {
                  const sorted = [...data].sort(
                    (a, b) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime()
                  );
                  setAnalyses(sorted);
                })
                .catch((err) => {
                  const msg = (err as Partial<ApiError>).message ?? 'Error al actualizar.';
                  showToast('error', 'Error', msg);
                })
                .finally(() => setIsLoading(false));
            }}
            aria-label="Actualizar historial"
            title="Actualizar historial"
            id="dashboard-refresh-btn"
          >
            ⟳ Actualizar
          </button>
          <button
            id="dashboard-new-analysis-btn"
            className="btn btn-primary"
            onClick={() => void navigate('/workspace')}
            aria-label="Nuevo análisis de frotis"
          >
            <span aria-hidden="true">⊕</span> Nuevo análisis
          </button>
        </div>
      </header>

      {/* Stats (solo cuando hay datos) */}
      {!isLoading && !loadError && analyses.length > 0 && (
        <StatsRow analyses={analyses} />
      )}

      {/* Toolbar de búsqueda */}
      {!isLoading && !loadError && analyses.length > 0 && (
        <div className="dashboard-toolbar animate-fade-in">
          <div className="dashboard-search-wrapper">
            <span className="dashboard-search-icon" aria-hidden="true">🔍</span>
            <input
              id="dashboard-search"
              type="search"
              className="form-input dashboard-search"
              placeholder="Buscar por tipo celular, estado o ID…"
              value={searchQuery}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              aria-label="Buscar en historial de análisis"
            />
          </div>
          <span className="dashboard-count" aria-live="polite">
            {filtered.length} análisis
          </span>
        </div>
      )}

      {/* Estados: cargando */}
      {isLoading && (
        <div className="dashboard-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton analysis-card-skeleton" />
          ))}
        </div>
      )}

      {/* Estado: error de carga */}
      {!isLoading && loadError && (
        <div className="empty-state animate-fade-in">
          <span className="empty-state-icon" aria-hidden="true">⚠️</span>
          <h2 className="empty-state-title">No se pudo cargar el historial</h2>
          <p className="empty-state-description">{loadError}</p>
          <button
            className="btn btn-primary"
            onClick={() => window.location.reload()}
            id="retry-load-btn"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Estado: sin resultados de búsqueda */}
      {!isLoading && !loadError && filtered.length === 0 && analyses.length > 0 && (
        <div className="empty-state animate-fade-in">
          <span className="empty-state-icon" aria-hidden="true">🔍</span>
          <h2 className="empty-state-title">Sin resultados</h2>
          <p className="empty-state-description">
            No se encontraron análisis para &ldquo;{searchQuery}&rdquo;.
          </p>
          <button
            className="btn btn-ghost"
            onClick={() => setSearchQuery('')}
            id="clear-search-btn"
          >
            Limpiar búsqueda
          </button>
        </div>
      )}

      {/* Estado: historial vacío */}
      {!isLoading && !loadError && analyses.length === 0 && (
        <div className="empty-state animate-fade-in">
          <span className="empty-state-icon" aria-hidden="true">🧫</span>
          <h2 className="empty-state-title">Sin análisis aún</h2>
          <p className="empty-state-description">
            Realiza tu primer análisis de frotis sanguíneo para comenzar.
          </p>
          <button
            id="empty-new-analysis-btn"
            className="btn btn-primary"
            onClick={() => void navigate('/workspace')}
          >
            Comenzar análisis
          </button>
        </div>
      )}

      {/* Grid de tarjetas */}
      {!isLoading && !loadError && filtered.length > 0 && (
        <div className="dashboard-grid stagger-children">
          {filtered.map((analysis) => (
            <AnalysisCard
              key={analysis.id}
              analysis={analysis}
              onClick={() => void navigate(`/analysis/${analysis.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
