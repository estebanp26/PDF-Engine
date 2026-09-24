import React from 'react';
import { ArrowRight, Search, FileText } from 'lucide-react';

export default function SearchResultsTab({
  searchResults,
  onJumpToPage,
  searchQuery
}) {
  const results = searchResults?.results || [];

  if (results.length === 0) {
    return (
      <div className="py-16 text-center text-slate-400">
        <Search className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
        <p className="text-sm font-medium">No hay coincidencias activas</p>
        <p className="text-xs text-slate-500 mt-1">
          {searchQuery ? `No se encontraron resultados para "${searchQuery}"` : 'Realiza una búsqueda desde la barra superior'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-800">
        <span>{results.length} coincidencias encontradas</span>
        <span>Haz clic en "Ver en Visor" para saltar a la página resaltada</span>
      </div>

      <div className="space-y-2.5">
        {results.map((item, idx) => {
          const matchedWord = item.matched_term || item.token_searched || searchQuery;
          const safeWord = (item.matched_term || searchQuery || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          const safeQuery = (searchQuery || '').trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          const highlightPattern = safeWord || safeQuery;
          const parts = highlightPattern
            ? item.snippet.split(new RegExp(`(${highlightPattern})`, 'gi'))
            : [item.snippet];

          return (
            <div
              key={idx}
              className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg hover:border-slate-300 dark:hover:border-slate-700 transition shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
            >
              <div className="space-y-1 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-xs text-slate-900 dark:text-white flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                    <span>Página {item.page}</span>
                  </span>

                  <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    — {item.source_label}
                  </span>

                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
                    {item.match_type === 'prefijo'
                      ? `"${item.matched_term}" (prefijo de "${searchQuery}")`
                      : item.match_type === 'subcadena'
                      ? `"${item.matched_term}" (contiene "${searchQuery}")`
                      : `"${item.matched_term || matchedWord}" (${item.match_type})`}
                  </span>
                </div>

                <div className="text-xs text-slate-600 dark:text-slate-300 font-sans leading-relaxed">
                  {parts.map((p, pIdx) => {
                    const isMatch = highlightPattern && new RegExp(`^(${highlightPattern})$`, 'i').test(p);
                    return isMatch ? (
                      <mark key={pIdx} className="bg-amber-200 dark:bg-amber-800/80 text-amber-950 dark:text-amber-100 px-1 py-0.5 rounded font-semibold">
                        {p}
                      </mark>
                    ) : (
                      <span key={pIdx}>{p}</span>
                    );
                  })}
                </div>
              </div>

              <button
                onClick={() => {
                  const coords = [item.x0, item.y0, item.x1, item.y1];
                  const rects = coords.every(c => c !== null && c !== undefined) ? coords : null;
                  onJumpToPage(item.page, item.matched_term || matchedWord, rects);
                }}
                className="shrink-0 flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-medium rounded-md transition"
              >
                <span>Ver en Visor</span>
                <ArrowRight className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
