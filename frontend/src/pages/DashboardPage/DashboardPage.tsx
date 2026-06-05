/**
 * pages/DashboardPage/DashboardPage.tsx
 * ---------------------------------------
 * Vista principal del historial de análisis.
 */

import { useState, useEffect, ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import type { AnalysisRecord } from '../../types/api';
import './DashboardPage.css';

// ---------------------------------------------------------------------------
// Mock data (reemplazar con API real cuando esté disponible)
// ---------------------------------------------------------------------------

function generateMockAnalyses(): AnalysisRecord[] {
  const classesList: string[][] = [
    ['Neutrófilo', 'Linfocito'],
    ['Monocito', 'Eosinófilo'],
    ['Basófilo', 'Neutrófilo', 'Linfocito'],
    ['Neutrófilo'],
    ['Linfocito', 'Monocito'],
    ['Eosinófilo', 'Neutrófilo'],
  ];
  const tipos = ['YOLOv8', 'Manual', 'YOLOv8', 'Manual', 'YOLOv8', 'Manual'];

  return Array.from({ length: 6 }, (_, i): AnalysisRecord => ({
    id:                `mock-${i + 1}`,
    analisis_id:       `550e8400-e29b-41d4-a716-4466554400${String(i).padStart(2, '0')}`,
    imagen_url:        null,
    estado:            'COMPLETED',
    total_detecciones: 8 + i * 3,
    clases_detectadas: classesList[i] ?? [],
    fecha:             new Date(Date.now() - i * 86_400_000 * 2).toISOString(),
    tipo:              tipos[i] ?? 'YOLOv8',
  }));
}

// ---------------------------------------------------------------------------
// Subcomponente: tarjeta de análisis
// ---------------------------------------------------------------------------

interface AnalysisCardProps {
  analysis: AnalysisRecord;
  onClick:  () => void;
}

function AnalysisCard({ analysis, onClick }: AnalysisCardProps) {
  const date    = new Date(analysis.fecha);
  const dateStr = date.toLocaleDateString('es-AR', { year: 'numeric', month: 'short', day: 'numeric' });
  const timeStr = date.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

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
        <div className="analysis-card-thumb-content" aria-hidden="true">
          <span className="analysis-card-thumb-icon">🔬</span>
          <span className="analysis-card-thumb-count">{analysis.total_detecciones}</span>
          <span className="analysis-card-thumb-unit">células</span>
        </div>
      </div>

      <div className="analysis-card-body">
        <div className="analysis-card-badges">
          <span className="badge badge-secondary">
            <span className="badge-dot" aria-hidden="true" />
            {analysis.estado}
          </span>
          <span className="badge badge-tertiary">{analysis.tipo}</span>
        </div>

        <h3 className="analysis-card-title">
          Análisis #{analysis.id.replace('mock-', '')}
        </h3>

        <div className="analysis-card-classes">
          {analysis.clases_detectadas.slice(0, 3).map((cls) => (
            <span key={cls} className="chip">{cls}</span>
          ))}
          {analysis.clases_detectadas.length > 3 && (
            <span className="chip">+{analysis.clases_detectadas.length - 3}</span>
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
  analyses: AnalysisRecord[];
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
  const [analyses,    setAnalyses]    = useState<AnalysisRecord[]>([]);
  const [isLoading,   setIsLoading]   = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnalyses(generateMockAnalyses());
      setIsLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  const filtered = analyses.filter((a) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.estado.toLowerCase().includes(q) ||
      a.clases_detectadas.some((c) => c.toLowerCase().includes(q))
    );
  });

  const userName = user?.email?.split('@')[0] ?? 'Usuario';

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <div className="dashboard-header-text animate-fade-in-up">
          <h1 className="dashboard-greeting">
            Buenas tardes, <span className="dashboard-greeting-name">{userName}</span>
          </h1>
          <p className="dashboard-subtitle">
            Aquí encontrarás todos tus análisis de frotis sanguíneos
          </p>
        </div>
        <button
          id="dashboard-new-analysis-btn"
          className="btn btn-primary"
          onClick={() => void navigate('/workspace')}
          aria-label="Nuevo análisis de frotis"
        >
          <span aria-hidden="true">⊕</span> Nuevo análisis
        </button>
      </header>

      {!isLoading && <StatsRow analyses={analyses} />}

      <div className="dashboard-toolbar animate-fade-in">
        <div className="dashboard-search-wrapper">
          <span className="dashboard-search-icon" aria-hidden="true">🔍</span>
          <input
            id="dashboard-search"
            type="search"
            className="form-input dashboard-search"
            placeholder="Buscar por tipo celular o estado…"
            value={searchQuery}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
            aria-label="Buscar en historial de análisis"
          />
        </div>
        <span className="dashboard-count" aria-live="polite">
          {isLoading ? '…' : `${filtered.length} análisis`}
        </span>
      </div>

      {isLoading ? (
        <div className="dashboard-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton analysis-card-skeleton" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state animate-fade-in">
          <span className="empty-state-icon" aria-hidden="true">🧫</span>
          <h2 className="empty-state-title">
            {searchQuery ? 'Sin resultados' : 'Sin análisis aún'}
          </h2>
          <p className="empty-state-description">
            {searchQuery
              ? `No se encontraron análisis para "${searchQuery}".`
              : 'Realiza tu primer análisis de frotis sanguíneo para comenzar.'}
          </p>
          {!searchQuery && (
            <button
              id="empty-new-analysis-btn"
              className="btn btn-primary"
              onClick={() => void navigate('/workspace')}
            >
              Comenzar análisis
            </button>
          )}
        </div>
      ) : (
        <div className="dashboard-grid stagger-children">
          {filtered.map((analysis) => (
            <AnalysisCard
              key={analysis.id}
              analysis={analysis}
              onClick={() => void navigate('/workspace', { state: { analysis } })}
            />
          ))}
        </div>
      )}
    </div>
  );
}
