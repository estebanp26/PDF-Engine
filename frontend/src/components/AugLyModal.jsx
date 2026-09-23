import React, { useState } from 'react';
import { Sparkles, X, Check, Download, Zap } from 'lucide-react';

export default function AugLyModal({
  isOpen,
  onClose,
  onScanGenerated
}) {
  const [pages, setPages] = useState(20);
  const [images, setImages] = useState(4);
  const [density, setDensity] = useState('repleta');
  const [degradation, setDegradation] = useState('mixed_all');
  const [keywords, setKeywords] = useState('HABLAR, AHORA, CONFIDENCIAL_AUG, TOTAL_PAGAR');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setGenerating(true);
    setResult(null);

    try {
      const res = await fetch('/api/generate-random-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pages: parseInt(pages) || 20,
          images_count: parseInt(images) || 4,
          text_density: density,
          degradation: degradation,
          keywords: keywords
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setResult(data);
      } else {
        alert('Error generando PDF con AugLy: ' + (data.detail || 'Error'));
      }
    } catch (err) {
      alert('Error de conexión: ' + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleScanNow = () => {
    if (result && result.file_path) {
      onScanGenerated(result);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl w-full max-w-lg p-5 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-950/70 text-purple-600 dark:text-purple-400 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Generador Sintético con AugLy</h3>
              <p className="text-[11px] text-slate-500">Crea documentos realistas con degradación de imágenes (Meta AugLy)</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Configuration Form */}
        <div className="space-y-3.5 text-xs">
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                Cantidad de Páginas
              </label>
              <input
                type="number"
                min="1"
                max="60"
                value={pages}
                onChange={(e) => setPages(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                Cantidad de Imágenes
              </label>
              <input
                type="number"
                min="0"
                max="20"
                value={images}
                onChange={(e) => setImages(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
          </div>

          <div>
            <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
              Densidad de Texto
            </label>
            <select
              value={density}
              onChange={(e) => setDensity(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="repleta">Repleta de Texto (Máxima densidad, contratos y auditoría)</option>
              <option value="media">Media (Facturas, tablas y párrafos estándar)</option>
              <option value="baja">Baja (Títulos, resúmenes cortos)</option>
            </select>
          </div>

          <div>
            <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
              Degradación y Efectos AugLy
            </label>
            <select
              value={degradation}
              onChange={(e) => setDegradation(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="mixed_all">Mix Realista (Digital + Escaneos Sucios + Fotos Inclinadas)</option>
              <option value="scanned_noise">Escáner Antiguo y Ruidoso (Ruido Gaussiano + Desenfoque)</option>
              <option value="low_contrast">Fotocopia / Bajo Contraste (Atenuación)</option>
              <option value="skew_perspective">Perspectiva Inclinada y Distorsión (Skew)</option>
              <option value="clean">Limpio / Digital sin ruido</option>
            </select>
          </div>

          <div>
            <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
              Palabras Clave a Inyectar (Separadas por coma)
            </label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
            <span className="text-[11px] text-slate-400 block mt-0.5">
              Se inyectarán en texto digital y dentro de imágenes para probar la búsqueda.
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 border border-slate-300 dark:border-slate-700 rounded-md text-slate-700 dark:text-slate-300 font-medium hover:bg-slate-100 transition"
            >
              Cancelar
            </button>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-purple-700 hover:bg-purple-800 dark:bg-purple-600 dark:hover:bg-purple-700 text-white font-semibold rounded-md shadow-sm transition disabled:opacity-50"
            >
              {generating ? (
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <Sparkles className="w-3.5 h-3.5" />
              )}
              <span>Generar con AugLy</span>
            </button>
          </div>

        </div>

        {/* Result Area */}
        {result && (
          <div className="p-3.5 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800/80 rounded-lg text-xs space-y-2.5 mt-3 animate-fade-in">
            <div className="flex items-center gap-1.5 font-bold text-purple-900 dark:text-purple-200">
              <Check className="w-4 h-4 text-emerald-600" />
              <span>PDF Generado con Éxito</span>
            </div>

            <div className="text-slate-700 dark:text-slate-300 space-y-0.5">
              <div><b>Archivo:</b> {result.filename} ({result.file_size_kb} KB)</div>
              <div><b>Estructura:</b> {result.total_pages} páginas, {result.images_count} imágenes procesadas con AugLy</div>
              <div className="text-[11px] text-slate-500 pt-1">
                <b>Palabras Inyectadas:</b> {(result.injected_keywords || []).map(k => `${k.term} (p.${k.page})`).join(', ')}
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button
                onClick={handleScanNow}
                className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-md shadow-sm transition"
              >
                <Zap className="w-4 h-4" />
                <span>🚀 Escanear y Procesar Ahora</span>
              </button>

              <a
                href={`/api/download-generated/${result.filename}`}
                download
                className="px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-md font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 flex items-center gap-1"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Descargar</span>
              </a>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
