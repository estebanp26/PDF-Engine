import React from 'react';
import { Search, X, Sparkles } from 'lucide-react';

export default function SearchBar({
  searchQuery,
  setSearchQuery,
  onSearch,
  searchResult,
  searching
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  const handleClear = () => {
    setSearchQuery('');
  };

  const totalMatches = searchResult?.total_matches || 0;
  const matchedPagesCount = searchResult?.matched_pages?.length || 0;
  const latencyMs = searchResult?.search_latency_ms;
  const tokens = searchResult?.tokens || [];

  return (
    <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm mb-6 transition">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-5 h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar palabras en texto digital o dentro de imágenes/escaneos (ej. Factura, Andres Teheran, hablar ahora)..."
            className="w-full pl-11 pr-10 py-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-md text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition"
          />
          {searchQuery && (
            <button
              onClick={handleClear}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <button
          onClick={onSearch}
          disabled={searching}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-700 hover:bg-blue-800 dark:bg-blue-600 dark:hover:bg-blue-700 text-white font-medium text-sm rounded-md shadow-sm transition disabled:opacity-50"
        >
          {searching ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          ) : (
            <Search className="w-4 h-4" />
          )}
          <span>Buscar</span>
        </button>
      </div>

      {/* Search Meta Summary */}
      <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/60">
        <div>
          {searchResult ? (
            <span>
              <b>{totalMatches}</b> coincidencia(s) en <b>{matchedPagesCount}</b> página(s)
              {tokens.length > 0 && (
                <span className="ml-1 text-slate-400">
                  [Términos independientes: {tokens.map(t => `"${t}"`).join(', ')}]
                </span>
              )}
            </span>
          ) : (
            <span>Ingresa una o varias palabras para buscar de forma simultánea en texto e imágenes OCR.</span>
          )}
        </div>

        {latencyMs !== undefined && (
          <div className="flex items-center gap-1 font-semibold text-blue-700 dark:text-blue-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>⚡ {latencyMs} ms</span>
          </div>
        )}
      </div>
    </section>
  );
}
