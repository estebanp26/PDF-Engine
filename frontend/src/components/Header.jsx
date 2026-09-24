import React from 'react';
import { Sun, Moon, Upload, FileText, CheckCircle2 } from 'lucide-react';

export default function Header({
  darkMode,
  setDarkMode,
  onLoadBenchmark,
  onUploadClick,
  documentData
}) {
  return (
    <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40 transition-colors shadow-xs">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">

        {/* Brand Area */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-700 dark:bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-xs">
            PE
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 dark:text-white text-base tracking-tight">PDF-Engine</span>
              {documentData && (
                <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                  <CheckCircle2 className="w-3 h-3" />
                  Listo
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Dark Mode Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
            title="Alternar Modo Oscuro / Claro"
          >
            {darkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />}
            <span className="hidden sm:inline">{darkMode ? 'Claro' : 'Oscuro'}</span>
          </button>

          {/* Benchmark Load */}
          <button
            onClick={onLoadBenchmark}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
            title="Cargar documento de prueba (20 Páginas)"
          >
            <FileText className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
            <span>Demo 20 Págs</span>
          </button>

          {/* Upload Button */}
          <button
            onClick={onUploadClick}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-md bg-blue-700 hover:bg-blue-800 dark:bg-blue-600 dark:hover:bg-blue-700 text-white transition shadow-xs"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{documentData ? 'Cambiar PDF' : 'Subir PDF'}</span>
          </button>
        </div>

      </div>
    </header>
  );
}