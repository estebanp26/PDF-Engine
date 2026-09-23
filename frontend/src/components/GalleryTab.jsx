import React from 'react';
import { Image as ImageIcon, Eye } from 'lucide-react';

export default function GalleryTab({ pages, onJumpToPage }) {
  const allImages = [];
  (pages || []).forEach(p => {
    (p.images || []).forEach(img => {
      allImages.push({ ...img, pageNumber: p.page });
    });
  });

  if (allImages.length === 0) {
    return (
      <div className="py-16 text-center text-slate-400">
        <ImageIcon className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
        <p className="text-sm font-medium">No se detectaron imágenes embebidas</p>
        <p className="text-xs text-slate-500 mt-1">Este documento está compuesto únicamente de streams de texto o páginas estándar.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-800">
        <span>{allImages.length} imágenes extraídas en binario directamente del PDF</span>
        <span>Procesadas en paralelo con filtros Anti-Todo</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {allImages.map(img => (
          <div
            key={img.id}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden shadow-xs flex flex-col"
          >
            {/* Image Preview */}
            <div className="h-44 bg-slate-100 dark:bg-slate-950 flex items-center justify-center p-2 border-b border-slate-200 dark:border-slate-800 relative group">
              <img
                src={`/api/extracted-image/${img.id}`}
                alt={img.id}
                className="max-h-full max-w-full object-contain"
                loading="lazy"
              />
              <button
                onClick={() => onJumpToPage(img.pageNumber)}
                className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 flex items-center justify-center gap-1.5 text-white text-xs font-semibold transition"
              >
                <Eye className="w-4 h-4" />
                <span>Ver en Página {img.pageNumber}</span>
              </button>
            </div>

            {/* Info Body */}
            <div className="p-3 flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-bold text-slate-900 dark:text-white">{img.id}</span>
                  <span className="text-[11px] text-slate-400">
                    Pág. {img.pageNumber} • {img.width}x{img.height} ({img.format})
                  </span>
                </div>

                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Texto Recuperado por OCR:
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/80 rounded p-2 text-xs font-mono text-slate-700 dark:text-slate-300 max-h-24 overflow-y-auto leading-tight">
                  {img.ocr_text || <span className="italic text-slate-400">Sin texto detectable en imagen</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
