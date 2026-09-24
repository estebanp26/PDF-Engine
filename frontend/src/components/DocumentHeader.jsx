import React from 'react';
import { FileText, CheckCircle2, Zap, Clock, X } from 'lucide-react';

export default function DocumentHeader({ documentData, onClose }) {
  if (!documentData) return null;

  const totalPages = documentData.total_pages || 1;
  const isScanned = documentData.ocr_pages > 0;
  const totalSeconds = documentData.metrics?.total_seconds;

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-3 sm:px-4 sm:py-2.5 mb-5 flex flex-wrap items-center justify-between gap-3 shadow-2xs">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-8 h-8 rounded-md bg-blue-50 dark:bg-blue-950/70 border border-blue-200 dark:border-blue-800 flex items-center justify-center shrink-0">
          <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="min-w-0">
          <div className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-white truncate">
            {documentData.filename}
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
            <span>{totalPages} {totalPages === 1 ? 'página' : 'páginas'}</span>
            <span>•</span>
            <span className={isScanned ? 'text-amber-600 dark:text-amber-400' : 'text-slate-600 dark:text-slate-300'}>
              {isScanned ? 'Escaneo OCR' : 'Texto Digital'}
            </span>
            {totalSeconds && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                  <Zap className="w-3 h-3" />
                  {totalSeconds}s
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          title="Cerrar documento actual"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
