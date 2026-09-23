import React from 'react';

export default function LoadingOverlay({ isLoading, title, desc }) {
  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-2xs">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-6 flex flex-col items-center gap-3 text-center max-w-sm w-full animate-fade-in">
        <div className="w-9 h-9 border-3 border-slate-200 dark:border-slate-700 border-t-blue-600 rounded-full animate-spin"></div>
        <div className="font-bold text-sm text-slate-900 dark:text-white">
          {title || 'Procesando...'}
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400">
          {desc || 'Ejecutando operaciones en paralelo...'}
        </div>
      </div>
    </div>
  );
}
