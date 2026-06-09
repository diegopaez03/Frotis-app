/**
 * components/ImageViewer/ImageViewer.tsx
 * ----------------------------------------
 * Visor interactivo de imagen con zoom, pan y overlay de bounding boxes.
 */

import {
  useRef,
  useState,
  useCallback,
  useEffect,
  MouseEvent as ReactMouseEvent,
  TouchEvent as ReactTouchEvent,
} from 'react';
import type { DeteccionItem, FeedbackItem } from '../../types/api';
import './ImageViewer.css';

// ---------------------------------------------------------------------------
// Paleta de colores por clase
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
// Constantes de zoom
// ---------------------------------------------------------------------------

const MIN_ZOOM  = 0.3;
const MAX_ZOOM  = 5.0;
const ZOOM_STEP = 0.25;

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface ImageViewerProps {
  imageUrl?:   string | null;
  detections?: DeteccionItem[];
  showBboxes?: boolean;
  className?:  string;
  // Feedback props
  feedbackMode?: boolean;
  drawTool?: 'pan' | 'draw';
  onSelectDetection?: (det: DeteccionItem) => void;
  onDrawBbox?: (bbox: [number, number, number, number]) => void;
  pendingFeedbacks?: FeedbackItem[];
}

interface Offset      { x: number; y: number; }
interface NaturalSize { w: number; h: number; }

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export default function ImageViewer({
  imageUrl   = null,
  detections = [],
  showBboxes = true,
  className  = '',
  feedbackMode = false,
  drawTool = 'pan',
  onSelectDetection,
  onDrawBbox,
  pendingFeedbacks = [],
}: ImageViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef       = useRef<HTMLImageElement>(null);

  const [zoom,           setZoom]           = useState(1);
  const [offset,         setOffset]         = useState<Offset>({ x: 0, y: 0 });
  const [isDragging,     setIsDragging]     = useState(false);
  const [dragStart,      setDragStart]      = useState<Offset>({ x: 0, y: 0 });
  const [imgNaturalSize, setImgNaturalSize] = useState<NaturalSize>({ w: 0, h: 0 });
  const [imgLoaded,      setImgLoaded]      = useState(false);
  const [imgError,       setImgError]       = useState(false);

  // Drawing state
  const [isDrawingBbox, setIsDrawingBbox]     = useState(false);
  const [drawStartFrac, setDrawStartFrac]     = useState<Offset | null>(null);
  const [drawCurrentFrac, setDrawCurrentFrac] = useState<Offset | null>(null);

  // Resetear estado cuando cambia la URL
  useEffect(() => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
    setImgLoaded(false);
    setImgError(false);
  }, [imageUrl]);

  /**
   * Detectar imágenes ya en caché del navegador.
   * El evento `onLoad` de React NO se dispara si la imagen ya estaba cacheada.
   * Verificamos `img.complete` en el siguiente tick (después de que React
   * actualice el DOM con el nuevo src).
   */
  useEffect(() => {
    if (!imageUrl) return;
    const timer = setTimeout(() => {
      const img = imgRef.current;
      if (img && img.complete && img.naturalWidth > 0) {
        setImgNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
        setImgLoaded(true);
      }
    }, 0);
    return () => clearTimeout(timer);
  }, [imageUrl]);

  // Handler para el evento onLoad de React (imágenes no cacheadas)
  const handleImgLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>): void => {
    setImgNaturalSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight });
    setImgLoaded(true);
  }, []);

  // Zoom con rueda del mouse (pasivo: prevenimos default via addEventListener)
  const handleWheel = useCallback((e: Event): void => {
    e.preventDefault();
    const we = e as unknown as { deltaY: number };
    const delta = we.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
    setZoom((z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z + delta)));
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  // Pan / Draw — mouse
  const handleMouseDown = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>): void => {
      if (e.button !== 0) return;

      if (feedbackMode && drawTool === 'draw') {
        e.preventDefault();
        const imgEl = imgRef.current;
        if (!imgEl) return;
        const rect = imgEl.getBoundingClientRect();
        
        // Calcular fracción dentro de la imagen
        const startX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const startY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
        
        setIsDrawingBbox(true);
        setDrawStartFrac({ x: startX, y: startY });
        setDrawCurrentFrac({ x: startX, y: startY });
        return;
      }

      e.preventDefault();
      setIsDragging(true);
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    },
    [offset, feedbackMode, drawTool]
  );

  const handleMouseMove = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>): void => {
      if (isDrawingBbox) {
        const imgEl = imgRef.current;
        if (!imgEl) return;
        const rect = imgEl.getBoundingClientRect();
        
        const curX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const curY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
        
        setDrawCurrentFrac({ x: curX, y: curY });
        return;
      }

      if (!isDragging) return;
      setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    },
    [isDragging, dragStart, isDrawingBbox]
  );

  const handleMouseUp = useCallback((): void => {
    if (isDrawingBbox) {
      setIsDrawingBbox(false);
      if (drawStartFrac && drawCurrentFrac && imgNaturalSize.w > 0 && imgNaturalSize.h > 0) {
        const xMin = Math.min(drawStartFrac.x, drawCurrentFrac.x) * imgNaturalSize.w;
        const yMin = Math.min(drawStartFrac.y, drawCurrentFrac.y) * imgNaturalSize.h;
        const xMax = Math.max(drawStartFrac.x, drawCurrentFrac.x) * imgNaturalSize.w;
        const yMax = Math.max(drawStartFrac.y, drawCurrentFrac.y) * imgNaturalSize.h;
        
        const w = xMax - xMin;
        const h = yMax - yMin;
        
        // Solo emitir si cumple con un tamaño mínimo razonable (ej. 8 píxeles naturales)
        if (w > 8 && h > 8) {
          onDrawBbox?.([xMin, yMin, xMax, yMax]);
        }
      }
      setDrawStartFrac(null);
      setDrawCurrentFrac(null);
      return;
    }
    
    setIsDragging(false);
  }, [isDrawingBbox, drawStartFrac, drawCurrentFrac, imgNaturalSize, onDrawBbox]);

  // Pan — touch
  const touchStartRef = useRef<Offset | null>(null);

  const handleTouchStart = useCallback(
    (e: ReactTouchEvent<HTMLDivElement>): void => {
      if (e.touches.length === 1) {
        const touch = e.touches[0];
        touchStartRef.current = { x: touch.clientX - offset.x, y: touch.clientY - offset.y };
      }
    },
    [offset]
  );

  const handleTouchMove = useCallback(
    (e: ReactTouchEvent<HTMLDivElement>): void => {
      if (e.touches.length === 1 && touchStartRef.current) {
        const touch = e.touches[0];
        setOffset({
          x: touch.clientX - touchStartRef.current.x,
          y: touch.clientY - touchStartRef.current.y,
        });
      }
    },
    []
  );

  const handleTouchEnd = useCallback((): void => { touchStartRef.current = null; }, []);

  // Controles
  const zoomIn    = (): void => setZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP));
  const zoomOut   = (): void => setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP));
  const resetView = (): void => { setZoom(1); setOffset({ x: 0, y: 0 }); };

  // Renderizar bboxes
  function renderBboxes(): React.ReactNode {
    if (!showBboxes || !imgLoaded) return null;
    if (imgNaturalSize.w === 0 || imgNaturalSize.h === 0) return null;

    const imgEl = imgRef.current;
    if (!imgEl) return null;

    const renderedW = imgEl.clientWidth;
    const renderedH = imgEl.clientHeight;
    const scaleX    = renderedW / imgNaturalSize.w;
    const scaleY    = renderedH / imgNaturalSize.h;

    // Modificaciones por feedback pendiente
    const renderedDetections = detections.map((det) => {
      const fb = pendingFeedbacks?.find((f) => f.deteccion_id === det.id);
      if (fb) {
        if (fb.tipoCorreccion === 'FALSO_POSITIVO') {
          return { ...det, isFalsePositive: true };
        }
        if (fb.tipoCorreccion === 'CAMBIO_CLASE') {
          return {
            ...det,
            clase: fb.claseCorregida || det.clase,
            isClassChanged: true,
          };
        }
      }
      return det;
    });

    // Agregar nuevas detecciones manuales
    const newDetections = pendingFeedbacks
      ?.filter((f) => f.tipoCorreccion === 'NUEVA_DETECCION' && f.bbox_corregido)
      .map((f, index) => ({
        id: `new-${index}`,
        clase: f.claseCorregida || 'Linfocito',
        confianza: 1.0,
        bbox: f.bbox_corregido!,
        isNew: true,
      })) || [];

    const allDetections = [...renderedDetections, ...newDetections];

    return allDetections.map((det, idx) => {
      const [x1, y1, x2, y2] = det.bbox;
      const left   = x1 * scaleX;
      const top    = y1 * scaleY;
      const width  = (x2 - x1) * scaleX;
      const height = (y2 - y1) * scaleY;

      const isFP = 'isFalsePositive' in det && det.isFalsePositive;
      const isNew = 'isNew' in det && det.isNew;
      const isCC = 'isClassChanged' in det && det.isClassChanged;

      let color = getColorForClass(det.clase);
      let borderStyle = 'solid';
      let opacity = 1;
      let labelSuffix = '';

      if (isFP) {
        color = 'var(--color-error)';
        borderStyle = 'dashed';
        opacity = 0.4;
        labelSuffix = ' [Falso Positivo]';
      } else if (isNew) {
        borderStyle = 'dashed';
        labelSuffix = ' [Nueva]';
      } else if (isCC) {
        labelSuffix = ' [Corregida]';
      } else {
        labelSuffix = ` ${Math.round(det.confianza * 100)}%`;
      }

      return (
        <div
          key={det.id || idx}
          className={`bbox${isFP ? ' is-fp' : ''}${isNew ? ' is-new' : ''}${isCC ? ' is-cc' : ''}`}
          style={{
            position: 'absolute',
            left,
            top,
            width,
            height,
            border: `2px ${borderStyle} ${color}`,
            boxSizing: 'border-box',
            opacity,
            pointerEvents: feedbackMode && !isFP ? 'auto' : 'none',
            cursor: feedbackMode && !isFP ? 'pointer' : 'default',
          }}
          onClick={(e) => {
            if (feedbackMode && onSelectDetection && !isFP && !isNew) {
              e.stopPropagation();
              onSelectDetection(det as DeteccionItem);
            }
          }}
          title={`${det.clase}${labelSuffix}`}
        >
          <span className="bbox-label" style={{ background: color, color: '#fff', top: '-20px', left: '-1px' }}>
            {det.clase}{labelSuffix}
          </span>
        </div>
      );
    });
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className={`image-viewer ${className}`} aria-label="Visor de imagen de frotis">
      {/* Barra de controles */}
      <div className="image-viewer-controls" role="toolbar" aria-label="Controles del visor">
        <button className="btn btn-ghost btn-sm" onClick={zoomOut} id="viewer-zoom-out" aria-label="Reducir zoom">−</button>
        <span   className="viewer-zoom-label" aria-live="polite">{Math.round(zoom * 100)}%</span>
        <button className="btn btn-ghost btn-sm" onClick={zoomIn}  id="viewer-zoom-in"  aria-label="Aumentar zoom">+</button>
        <div    className="viewer-controls-divider" aria-hidden="true" />
        <button className="btn btn-ghost btn-sm" onClick={resetView} id="viewer-reset" aria-label="Restablecer vista">⟳</button>
        {imageUrl && (
          <a
            className="btn btn-ghost btn-sm"
            href={imageUrl}
            target="_blank"
            rel="noopener noreferrer"
            id="viewer-open-original"
            aria-label="Abrir imagen original en nueva pestaña"
          >↗</a>
        )}
      </div>

      {/* Viewport */}
      <div
        ref={containerRef}
        className={`image-viewer-viewport${isDragging ? ' is-dragging' : ''}${feedbackMode && drawTool === 'draw' ? ' draw-mode' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        role="img"
        aria-label="Imagen de frotis sanguíneo"
      >
        {/* Sin imagen */}
        {!imageUrl && (
          <div className="viewer-placeholder">
            <span className="viewer-placeholder-icon" aria-hidden="true">🔬</span>
            <p>Sube una imagen de frotis para comenzar el análisis</p>
          </div>
        )}

        {/* Error de carga */}
        {imageUrl && imgError && (
          <div className="viewer-placeholder viewer-error">
            <span aria-hidden="true">⚠</span>
            <p>No se pudo cargar la imagen.</p>
            <a href={imageUrl} target="_blank" rel="noopener noreferrer" className="viewer-error-link">
              Abrir URL directamente ↗
            </a>
          </div>
        )}

        {/* Imagen con zoom/pan */}
        {imageUrl && !imgError && (
          <>
            {/* Spinner de carga — sólo mientras la imagen no ha cargado */}
            {!imgLoaded && (
              <div className="viewer-loading-overlay" aria-label="Cargando imagen…">
                <div className="spinner" aria-hidden="true" />
                <p>Cargando imagen…</p>
              </div>
            )}

            <div
              className={`viewer-transform-layer${imgLoaded ? ' is-ready' : ''}`}
              style={{
                transform:       `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
                transformOrigin: 'center center',
              }}
            >
              <img
                ref={imgRef}
                src={imageUrl}
                alt="Frotis sanguíneo para análisis"
                className="viewer-image"
                onLoad={handleImgLoad}
                onError={() => setImgError(true)}
                draggable={false}
              />
              {imgLoaded && (
                <>
                  <div className="bbox-overlay" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
                    {renderBboxes()}
                  </div>
                  {isDrawingBbox && drawStartFrac && drawCurrentFrac && (
                    <div
                      className="bbox-drawing-temp"
                      style={{
                        position: 'absolute',
                        left: `${Math.min(drawStartFrac.x, drawCurrentFrac.x) * 100}%`,
                        top: `${Math.min(drawStartFrac.y, drawCurrentFrac.y) * 100}%`,
                        width: `${Math.abs(drawStartFrac.x - drawCurrentFrac.x) * 100}%`,
                        height: `${Math.abs(drawStartFrac.y - drawCurrentFrac.y) * 100}%`,
                        border: '2px dashed var(--color-primary)',
                        background: 'rgba(243, 116, 33, 0.15)',
                        boxSizing: 'border-box',
                        pointerEvents: 'none',
                        zIndex: 100,
                      }}
                    />
                  )}
                </>
              )}
            </div>
          </>
        )}
      </div>

      {imageUrl && imgLoaded && (
        <p className="viewer-hint">
          🖱 Rueda para zoom · Arrastra para mover
          {detections.length > 0 && ` · ${detections.length} detección${detections.length !== 1 ? 'es' : ''}`}
        </p>
      )}
    </div>
  );
}
