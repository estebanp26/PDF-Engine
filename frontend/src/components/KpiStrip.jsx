import React from 'react';
import { Timer, Zap, Layers, Brain } from 'lucide-react';

export default function KpiStrip({ documentData, aiResult }) {
  const metrics = documentData?.metrics || {};
  const breakdown = metrics.breakdown || {};
  
  const totalSeconds = metrics.total_seconds ? `${metrics.total_seconds} s` : '-- s';
  const totalMs = metrics.total_ms ? `(${metrics.total_ms} ms)` : '';
  const pagesPerSec = metrics.pages_per_second ? `${metrics.pages_per_second} págs/seg` : '0 págs/seg';
  
  const totalPages = documentData?.total_pages || 0;
  const filename = documentData?.filename || 'Ningún documento activo';
  
  const ocrSeconds = breakdown.parallel_ocr ? `${breakdown.parallel_ocr} s` : '-- s';
  const ocrItems = `${documentData?.ocr_items_processed || 0} elementos procesados`;
  
  const aiSeconds = aiResult?.latency_seconds ? `${aiResult.latency_seconds} s` : '-- s';
  const aiModel = aiResult?.model_used ? `${aiResult.model_used}` : 'Ollama local';

  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      
      {/* KPI 1: Total Speed */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm transition">
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
          <span>Tiempo Lectura + OCR</span>
          <Timer className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">{totalSeconds}</span>
          <span className="text-xs text-slate-500">{totalMs}</span>
        </div>
        <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium mt-1 flex items-center gap-1">
          <Zap className="w-3.5 h-3.5" />
          <span>{pagesPerSec}</span>
        </div>
      </div>

      {/* KPI 2: Total Pages */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm transition">
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
          <span>Páginas Procesadas</span>
          <Layers className="w-4 h-4 text-slate-500" />
        </div>
        <div className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">{totalPages}</div>
        <div className="text-xs text-slate-500 dark:text-slate-400 truncate mt-1" title={filename}>
          {filename}
        </div>
      </div>

      {/* KPI 3: Parallel OCR Pool */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm transition">
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
          <span>OCR Paralelo (12 Hilos)</span>
          <Zap className="w-4 h-4 text-amber-500" />
        </div>
        <div className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">{ocrSeconds}</div>
        <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          {ocrItems}
        </div>
      </div>

      {/* KPI 4: AI Latency */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm transition">
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
          <span>Inferencia IA (Qwen 2.5)</span>
          <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400" />
        </div>
        <div className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">{aiSeconds}</div>
        <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          {aiModel}
        </div>
      </div>

    </section>
  );
}
