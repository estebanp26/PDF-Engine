import React from 'react';

function progressTitle(p) {
  if (!p) return 'Procesando documento...';
  const stage = p.stage || 'processing';
  switch (stage) {
    case 'parsing':
      return `Analizando PDF... (${p.total_pages || '?'} páginas)`;
    case 'ocr':
      return p.ocr_total
        ? `Ejecutando OCR... ${p.ocr_done}/${p.ocr_total} elementos`
        : 'Ejecutando OCR...';
    case 'indexing':
      return 'Construyendo índice de búsqueda...';
    case 'finalizing':
      return 'Finalizando resultados...';
    case 'done':
      return p.cache_hit ? 'Documento cargado desde caché' : 'Documento procesado';
    default:
      return 'Procesando documento...';
  }
}

export default function LoadingOverlay({ isLoading, progress }) {
  if (!isLoading) return null;

  const percent = Math.min(100, Math.max(0, progress?.percent ?? 0));
  const p = progress || {};

  const digital = p.digital_pages !== undefined ? p.digital_pages : null;
  const ocrCount = p.ocr_pages !== undefined ? p.ocr_pages : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-2xs">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-6 flex flex-col items-center gap-3 text-center max-w-sm w-full animate-fade-in">
        <div className="w-9 h-9 border-3 border-slate-200 dark:border-slate-700 border-t-blue-600 rounded-full animate-spin"></div>
        <div className="font-bold text-sm text-slate-900 dark:text-white">
          {progressTitle(p)}
        </div>

        {/* Progress Bar */}
        <div className="w-full h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 dark:bg-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${percent}%` }}
          ></div>
        </div>
        <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
          {Math.round(percent)}% completado
        </div>

        {(digital !== null || ocrCount !== null) && (
          <div className="text-xs text-slate-600 dark:text-slate-300">
            {digital !== null && <span>Texto digital: {digital} páginas</span>}
            {digital !== null && ocrCount !== null && ' • '}
            {ocrCount !== null && <span>OCR: {ocrCount} páginas</span>}
          </div>
        )}

        <div className="text-[11px] text-slate-500 dark:text-slate-400">
          PyMuPDF + Tesseract + Qwen 2.5 (Ollama)
        </div>
      </div>
    </div>
  );
}