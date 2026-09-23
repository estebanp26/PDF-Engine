import React, { useState } from 'react';
import { FileText, Image as ImageIcon, Sparkles, Filter } from 'lucide-react';

export default function Sidebar({
  pages,
  activePage,
  onSelectPage,
  matchedPages = []
}) {
  const [filterMode, setFilterMode] = useState('all'); // 'all', 'matches', 'scanned'

  const matchedSet = new Set(matchedPages);

  const filteredPages = (pages || []).filter(p => {
    if (filterMode === 'matches') return matchedSet.has(p.page);
    if (filterMode === 'scanned') return p.is_scanned;
    return true;
  });

  return (
    <aside className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm flex flex-col h-[calc(100vh-320px)] min-h-[500px] transition">
      
      {/* Header */}
      <div className="p-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-850 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-slate-500" />
          <span className="font-semibold text-xs uppercase tracking-wider text-slate-700 dark:text-slate-300">
            Navegador ({pages?.length || 0} págs)
          </span>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 text-[11px]">
          <button
            onClick={() => setFilterMode('all')}
            className={`px-2 py-0.5 rounded ${filterMode === 'all' ? 'bg-blue-700 text-white font-medium' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
          >
            Todas
          </button>
          {matchedPages.length > 0 && (
            <button
              onClick={() => setFilterMode('matches')}
              className={`px-2 py-0.5 rounded ${filterMode === 'matches' ? 'bg-emerald-600 text-white font-medium' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
            >
              Coincidencias ({matchedPages.length})
            </button>
          )}
          <button
            onClick={() => setFilterMode('scanned')}
            className={`px-2 py-0.5 rounded ${filterMode === 'scanned' ? 'bg-amber-600 text-white font-medium' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
          >
            Escaneos
          </button>
        </div>
      </div>

      {/* Page List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5">
        {filteredPages.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            No hay páginas que coincidan con el filtro seleccionado.
          </div>
        ) : (
          filteredPages.map(p => {
            const isActive = p.page === activePage;
            const hasMatch = matchedSet.has(p.page);
            const imgCount = p.images?.length || 0;

            return (
              <div
                key={p.page}
                onClick={() => onSelectPage(p.page)}
                className={`flex items-center justify-between p-2.5 rounded-md border text-xs cursor-pointer transition ${
                  isActive 
                    ? 'border-blue-600 bg-blue-50/70 dark:bg-blue-950/40 text-blue-950 dark:text-blue-200 shadow-xs' 
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/80 hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <span>Página {p.page}</span>
                    {hasMatch && (
                      <span className="w-2 h-2 rounded-full bg-emerald-500" title="Contiene coincidencias de búsqueda"></span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5 mt-0.5">
                    <span>{p.is_scanned ? 'Escaneo OCR' : 'Texto digital'}</span>
                    {imgCount > 0 && (
                      <span className="flex items-center gap-0.5 text-slate-400">
                        • <ImageIcon className="w-3 h-3" /> {imgCount}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1">
                  {p.is_scanned ? (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                      OCR Scan
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      Digital
                    </span>
                  )}
                  {hasMatch && (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                      Match
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

    </aside>
  );
}
