import React from 'react';
import { Sun, Moon, Upload, FileText, Cpu } from 'lucide-react';

export default function Header({
  darkMode,
  setDarkMode,
  onLoadBenchmark,
  onUploadClick,
  systemStatus
}) {
  return (
    <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40 transition-colors shadow-sm">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">

        {/* Brand Area */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-700 dark:bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-sm">
            PE
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 dark:text-white text-lg tracking-tight">PDF-Engine</span>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-800">
                React + Vite
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 hidden sm:block">
              Motor C-Level Híbrido • OCR Paralelo • Inteligencia Artificial (Qwen 2.5)
            </p>
          </div>
        </div>

        {/* Telemetry Chip */}
        <div className="hidden md:flex items-center gap-2 text-xs font-medium bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 px-3.5 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          <span>{systemStatus?.cpu_cores || 6} núcleos • Tesseract 5.x • {systemStatus?.default_model || 'Qwen 2.5'}</span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* Dark Mode Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
            title="Alternar Modo Oscuro / Claro"
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
            <span className="hidden sm:inline">{darkMode ? 'Modo Claro' : 'Modo Oscuro'}</span>
          </button>

          {/* Benchmark Load */}
          <button
            onClick={onLoadBenchmark}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-750 transition"
            title="Cargar Benchmark Oficial de 20 Páginas"
          >
            <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span>Benchmark (20 Págs)</span>
          </button>

          {/* Upload Button */}
          <button
            onClick={onUploadClick}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-md bg-blue-700 hover:bg-blue-800 dark:bg-blue-600 dark:hover:bg-blue-700 text-white transition shadow-sm"
          >
            <Upload className="w-4 h-4" />
            <span>Subir PDF</span>
          </button>
        </div>

      </div>
    </header>
  );
}