import React, { useState } from 'react';
import { FileText, Image as ImageIcon } from 'lucide-react';

export default function Sidebar({
  pages,
  activePage,
  onSelectPage,
  matchedPages = []
}) {
  const [filterMode, setFilterMode] = useState('all');

  const matchedSet = new Set(matchedPages);

  const filteredPages = (pages || []).filter(p => {
    if (filterMode === 'matches') return matchedSet.has(p.page);
    if (filterMode === 'scanned') return p.is_scanned;
    return true;
  });

  return (
    <aside className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xs flex flex-col h-[calc(100vh-280px)] min-h-[460px] transition">
      
      {/* Header */}
      <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
          <span className="font-semibold text-xs text-slate-700 dark:text-slate-200">
            Páginas ({pages?.length || 0})
          </span>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 text-[11px]">
          <button
            onClick={() => setFilterMode('all')}
            className={`px-2 py-0.5 rounded transition ${filterMode === 'all' ? 'bg-blue-600 text-white font-medium' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
          >
            Todas
          </button>
          {matchedPages.length > 0 && (
            <button
              onClick={() => setFilterMode('matches')}
              className={`px-2 py-0.5 rounded transition ${filterMode === 'matches' ? 'bg-emerald-600 text-white font-medium' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
            >
              Hits ({matchedPages.length})
            </button>
          )}
        </div>
      </div>

      {/* Page List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filteredPages.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400 dark:text-slate-500">
            No hay páginas para este filtro.
          </div>
        ) : (
          filteredPages.map(p => {
            const isActive = p.page === activePage;
            const hasMatch = matchedSet.has(p.page);

            return (
              <div
                key={p.page}
                onClick={() => onSelectPage(p.page)}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs cursor-pointer transition ${
                  isActive 
                    ? 'border border-blue-600 bg-blue-50/80 dark:bg-blue-950/50 text-blue-900 dark:text-blue-200 font-semibold' 
                    : 'border border-transparent hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span>Pág. {p.page}</span>
                  {hasMatch && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" title="Contiene resultados"></span>
                  )}
                </div>

                <div className="text-[10px] text-slate-400 dark:text-slate-500">
                  {p.is_scanned ? 'OCR' : 'Texto'}
                </div>
              </div>
            );
          })
        )}
      </div>

    </aside>
  );
}
