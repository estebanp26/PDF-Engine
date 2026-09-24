import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import KpiStrip from './components/KpiStrip';
import SearchBar from './components/SearchBar';
import Sidebar from './components/Sidebar';
import AiExtractorTab from './components/AiExtractorTab';
import ViewerTab from './components/ViewerTab';
import SearchResultsTab from './components/SearchResultsTab';
import GalleryTab from './components/GalleryTab';
import LoadingOverlay from './components/LoadingOverlay';

export default function App() {
  // Theme state
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('pdf_engine_theme') === 'dark';
  });

  // Document & App State
  const [documentData, setDocumentData] = useState(null);
  const [activePage, setActivePage] = useState(1);
  const [activeTab, setActiveTab] = useState('ai'); // 'ai', 'viewer', 'search', 'gallery'

  // Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState(null);
  const [searching, setSearching] = useState(false);
  const [highlightQuery, setHighlightQuery] = useState('');
  const [highlightRects, setHighlightRects] = useState(null);

  // AI Extraction State
  const [targetFields, setTargetFields] = useState([
    "Número de Factura",
    "Proveedor Autorizado",
    "NIT",
    "Fecha de Emisión",
    "Valor Total a Pagar",
    "Responsable"
  ]);
  const [aiResult, setAiResult] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);

  // AI Question-Answering State
  const [askResult, setAskResult] = useState(null);
  const [askLoading, setAskLoading] = useState(false);

  // System & Job Progress State
  const [systemStatus, setSystemStatus] = useState(null);
  const [docJobId, setDocJobId] = useState(null);
  const [progress, setProgress] = useState(null);

  const fileInputRef = useRef(null);

  // Sync theme
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('pdf_engine_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('pdf_engine_theme', 'light');
    }
  }, [darkMode]);

  // Fetch system status on load
  useEffect(() => {
    fetch('/api/system-status')
      .then(res => res.json())
      .then(data => setSystemStatus(data))
      .catch(err => console.warn('Status error:', err));
  }, []);

  const loadDocumentJob = async (url, options) => {
    try {
      const res = await fetch(url, options);
      const data = await res.json();
      if (res.ok && data.job_id) {
        setProgress({ percent: 1 });
        setDocJobId(data.job_id);
      } else {
        alert('Error: ' + (data.detail || 'Error desconocido'));
        setProgress(null);
      }
    } catch (err) {
      alert('Error de red: ' + err.message);
      setProgress(null);
    }
  };

  // Poll job progress until done
  useEffect(() => {
    if (!docJobId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await fetch(`/api/progress/${docJobId}`);
        const data = await res.json();
        if (cancelled) return;
        if (data.progress) setProgress(data.progress);

        if (data.status === 'done') {
          clearInterval(timer);
          const docRes = await fetch(`/api/document/${docJobId}`);
          const docData = await docRes.json();
          if (docRes.ok && docData.success) {
            handleDocumentLoaded(docData);
          } else {
            alert('Error: ' + (docData.detail || 'Error obteniendo documento'));
          }
          setProgress(null);
          setDocJobId(null);
        } else if (data.status === 'error') {
          clearInterval(timer);
          alert('Error procesando documento: ' + (data.progress?.error || 'Error desconocido'));
          setProgress(null);
          setDocJobId(null);
        }
      } catch (e) { /* transient network error, keep polling */ }
    };

    const timer = setInterval(poll, 400);
    poll(); // immediate first check
    return () => { cancelled = true; clearInterval(timer); };
  }, [docJobId]);

  // Upload handler
  const handleUploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setProgress({ percent: 1 });
    await loadDocumentJob('/api/upload', { method: 'POST', body: formData });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Load sample benchmark
  const handleLoadBenchmark = async () => {
    setProgress({ percent: 1 });
    await loadDocumentJob('/api/load-sample', { method: 'POST' });
  };

  // Document loaded helper
  const handleDocumentLoaded = (data) => {
    setDocumentData(data);
    setActivePage(1);
    setSearchResult(null);
    setHighlightQuery('');
    setHighlightRects(null);
    setSearchQuery('');
    setAiResult(null);
    setAskResult(null);
  };

  // Perform multi-token search
  const handleSearch = async () => {
    const q = searchQuery.trim();
    if (!q) {
      setSearchResult(null);
      setHighlightQuery('');
      setHighlightRects(null);
      return;
    }
    if (!documentData) {
      alert('Carga un documento PDF primero.');
      return;
    }
    setSearching(true);
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q })
      });
      const data = await res.json();
      setSearchResult(data);
      setHighlightQuery(q);
      setHighlightRects(null);

      if (data.matched_pages?.length > 0) {
        setActivePage(data.matched_pages[0]);
      }
      setActiveTab('search');
    } catch (err) {
      alert('Error en búsqueda: ' + err.message);
    } finally {
      setSearching(false);
    }
  };

  // AI Extraction (fields)
  const handleRunAi = async (fields, model) => {
    if (!documentData) {
      alert('Carga un documento PDF primero.');
      return;
    }
    setLoadingAi(true);
    try {
      const res = await fetch('/api/extract-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields, model })
      });
      const data = await res.json();
      setAiResult(data);
    } catch (err) {
      alert('Error al consultar IA: ' + err.message);
    } finally {
      setLoadingAi(false);
    }
  };

  // AI Question-Answering
  const handleAsk = async (question, model) => {
    if (!documentData) {
      alert('Carga un documento PDF primero.');
      return;
    }
    setAskLoading(true);
    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, model })
      });
      const data = await res.json();
      setAskResult(data);
    } catch (err) {
      alert('Error al consultar IA: ' + err.message);
    } finally {
      setAskLoading(false);
    }
  };

  // Jump to specific page from search/gallery/answer
  const handleJumpToPage = (pageNum, term = null, rects = null) => {
    setActivePage(pageNum);
    if (term) setHighlightQuery(term);
    setHighlightRects(rects || null);
    setActiveTab('viewer');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">

      {/* Header */}
      <Header
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        onLoadBenchmark={handleLoadBenchmark}
        onUploadClick={() => fileInputRef.current?.click()}
        systemStatus={systemStatus}
      />

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleUploadFile}
        accept=".pdf"
        className="hidden"
      />

      {/* Main Container */}
      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 py-6">

        {/* Telemetry KPI Strip */}
        <KpiStrip
          documentData={documentData}
          aiResult={aiResult}
        />

        {/* Omnichannel Search Bar */}
        <SearchBar
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onSearch={handleSearch}
          searchResult={searchResult}
          searching={searching}
        />

        {/* Workspace Two-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6 items-start">

          {/* Left Column: Page Navigator Sidebar */}
          <Sidebar
            pages={documentData?.pages || []}
            activePage={activePage}
            onSelectPage={(p) => {
              setActivePage(p);
              setActiveTab('viewer');
            }}
            matchedPages={searchResult?.matched_pages || []}
          />

          {/* Right Column: Tabbed Content Area */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm min-h-[550px] flex flex-col transition">

            {/* Tab Navigation Bar */}
            <nav className="flex flex-wrap border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-850 px-4 gap-1">
              <button
                onClick={() => setActiveTab('ai')}
                className={`py-3 px-4 text-xs font-semibold border-b-2 transition ${
                  activeTab === 'ai'
                    ? 'border-blue-600 text-blue-700 dark:text-blue-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Extracción de Valores (IA)
              </button>

              <button
                onClick={() => setActiveTab('viewer')}
                className={`py-3 px-4 text-xs font-semibold border-b-2 transition ${
                  activeTab === 'viewer'
                    ? 'border-blue-600 text-blue-700 dark:text-blue-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Visor de Página ({activePage})
              </button>

              <button
                onClick={() => setActiveTab('search')}
                className={`py-3 px-4 text-xs font-semibold border-b-2 transition flex items-center gap-1.5 ${
                  activeTab === 'search'
                    ? 'border-blue-600 text-blue-700 dark:text-blue-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                <span>Resultados de Búsqueda</span>
                {searchResult?.total_matches > 0 && (
                  <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 text-[10px] font-bold flex items-center justify-center">
                    {searchResult.total_matches}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('gallery')}
                className={`py-3 px-4 text-xs font-semibold border-b-2 transition ${
                  activeTab === 'gallery'
                    ? 'border-blue-600 text-blue-700 dark:text-blue-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Imágenes & OCR
              </button>
            </nav>

            {/* Tab Panes */}
            <div className="p-4 sm:p-6 flex-1">
              {activeTab === 'ai' && (
                <AiExtractorTab
                  targetFields={targetFields}
                  setTargetFields={setTargetFields}
                  onRunAi={handleRunAi}
                  aiResult={aiResult}
                  loadingAi={loadingAi}
                  models={systemStatus?.available_models}
                  onAsk={handleAsk}
                  askResult={askResult}
                  askLoading={askLoading}
                  onAskJumpToPage={handleJumpToPage}
                />
              )}

              {activeTab === 'viewer' && (
                <ViewerTab
                  activePage={activePage}
                  totalPages={documentData?.total_pages || 1}
                  onPrevPage={() => setActivePage(p => Math.max(1, p - 1))}
                  onNextPage={() => setActivePage(p => Math.min(documentData?.total_pages || 1, p + 1))}
                  highlightQuery={highlightQuery}
                  highlightRects={highlightRects}
                  onClearHighlight={() => { setHighlightQuery(''); setHighlightRects(null); }}
                />
              )}

              {activeTab === 'search' && (
                <SearchResultsTab
                  searchResults={searchResult}
                  onJumpToPage={handleJumpToPage}
                  searchQuery={searchQuery}
                />
              )}

              {activeTab === 'gallery' && (
                <GalleryTab
                  pages={documentData?.pages || []}
                  onJumpToPage={handleJumpToPage}
                />
              )}
            </div>

          </section>

        </div>

      </main>

      {/* Loading Overlay with live progress */}
      <LoadingOverlay
        isLoading={!!docJobId}
        progress={progress}
      />

    </div>
  );
}