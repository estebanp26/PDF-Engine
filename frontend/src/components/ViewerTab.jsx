import React from 'react';
import { ChevronLeft, ChevronRight, Sparkles, X, Eye } from 'lucide-react';

export default function ViewerTab({
  activePage,
  totalPages,
  onPrevPage,
  onNextPage,
  highlightQuery,
  highlightRects,
  onClearHighlight
}) {
  const isFlatBox = Array.isArray(highlightRects) && highlightRects.length === 4 && typeof highlightRects[0] === 'number';
  const boxArray = isFlatBox ? [highlightRects] : highlightRects;
  const rectsParam = Array.isArray(boxArray) && boxArray.length
    ? `&rects=${encodeURIComponent(JSON.stringify(boxArray))}`
    : '';

  const previewUrl = activePage
    ? `/api/page-preview/${activePage}?t=${Date.now()}${highlightQuery ? `&highlight=${encodeURIComponent(highlightQuery)}` : ''}${rectsParam}`
    : null;

  return (
    <div className="space-y-4">
      
      {/* Viewer Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <Eye className="w-4 h-4 text-slate-500 dark:text-slate-400" />
          <span className="font-bold text-sm text-slate-900 dark:text-white">
            Página {activePage} de {totalPages || 1}
          </span>

          {highlightQuery && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
              <Sparkles className="w-3 h-3" />
              <span>Resaltando: "{highlightQuery}"</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {highlightQuery && (
            <button
              onClick={onClearHighlight}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
              title="Quitar resaltador de la vista previa"
            >
              <X className="w-3 h-3" />
              <span>Quitar Resaltado</span>
            </button>
          )}

          <button
            onClick={onPrevPage}
            disabled={activePage <= 1}
            className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 transition"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Anterior</span>
          </button>

          <button
            onClick={onNextPage}
            disabled={activePage >= totalPages}
            className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 transition"
          >
            <span>Siguiente</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Page Image Viewport */}
      <div className="flex justify-center items-center bg-slate-100 dark:bg-slate-950 p-4 sm:p-8 rounded-lg border border-slate-200 dark:border-slate-800 min-h-[500px] overflow-auto">
        {previewUrl ? (
          <img
            src={previewUrl}
            alt={`Página ${activePage}`}
            className="max-w-full max-h-[820px] object-contain bg-white shadow-md border border-slate-200 dark:border-slate-800 rounded transition"
            loading="lazy"
          />
        ) : (
          <div className="text-xs text-slate-400 dark:text-slate-500">
            Carga un documento para visualizar las páginas en alta resolución.
          </div>
        )}
      </div>

    </div>
  );
}
