import React, { useState } from 'react';
import { Brain, Plus, X, Copy, Check, Sparkles, Download } from 'lucide-react';

export default function AiExtractorTab({
  targetFields,
  setTargetFields,
  onRunAi,
  aiResult,
  loadingAi,
  models = ["qwen2.5:1.5b", "llama3.2:3b", "llava:7b"]
}) {
  const [newField, setNewField] = useState('');
  const [selectedModel, setSelectedModel] = useState('qwen2.5:1.5b');
  const [copiedKey, setCopiedKey] = useState(null);
  const [copiedJson, setCopiedJson] = useState(false);

  const handleAddField = () => {
    const trimmed = newField.trim();
    if (trimmed && !targetFields.includes(trimmed)) {
      setTargetFields([...targetFields, trimmed]);
      setNewField('');
    }
  };

  const handleRemoveField = (fieldToRemove) => {
    setTargetFields(targetFields.filter(f => f !== fieldToRemove));
  };

  const handleCopyValue = (key, val) => {
    navigator.clipboard.writeText(String(val));
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const handleCopyAllJson = () => {
    if (aiResult?.values) {
      navigator.clipboard.writeText(JSON.stringify(aiResult.values, null, 2));
      setCopiedJson(true);
      setTimeout(() => setCopiedJson(false), 2000);
    }
  };

  const handleExportCsv = () => {
    if (!aiResult?.values) return;
    const rows = [["Campo", "Valor Extraido"]];
    Object.entries(aiResult.values).forEach(([k, v]) => {
      rows.push([`"${k}"`, `"${String(v).replace(/"/g, '""')}"`]);
    });
    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `extraccion_ia_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const values = aiResult?.values || {};
  const hasValues = Object.keys(values).length > 0;

  return (
    <div className="space-y-6">
      
      {/* Configuration Area */}
      <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-lg border border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <h3 className="font-bold text-sm text-slate-900 dark:text-white">
              Campos y Valores a Extraer con IA
            </h3>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {targetFields.length} campos definidos
          </span>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 mb-3">
          El motor realiza poda de contexto (&lt; 600 tokens) para que Qwen 2.5 / Llava responda en tiempo récord.
        </p>

        {/* Tag Cloud */}
        <div className="flex flex-wrap gap-2 mb-3">
          {targetFields.map(f => (
            <span
              key={f}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 shadow-2xs"
            >
              <span>{f}</span>
              <button
                onClick={() => handleRemoveField(f)}
                className="text-slate-400 hover:text-red-500 font-bold ml-0.5"
                title="Eliminar campo"
              >
                &times;
              </button>
            </span>
          ))}
        </div>

        {/* Add Field Input */}
        <div className="flex gap-2 max-w-md mb-4">
          <input
            type="text"
            value={newField}
            onChange={(e) => setNewField(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddField()}
            placeholder="Agregar campo personalizado (ej. Teléfono, Ciudad)..."
            className="flex-1 px-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
          <button
            onClick={handleAddField}
            className="px-3 py-1.5 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 rounded-md text-xs font-medium flex items-center gap-1 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Agregar</span>
          </button>
        </div>

        {/* Controls row */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 block mb-1">
              Modelo IA (Ollama)
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-3 py-1.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              {models.map(m => (
                <option key={m} value={m}>{m} {m.includes('qwen2.5') ? '(Recomendado - Rápido)' : ''}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => onRunAi(targetFields, selectedModel)}
            disabled={loadingAi || targetFields.length === 0}
            className="mt-4 sm:mt-auto flex items-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-800 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-xs font-semibold rounded-md shadow-sm transition disabled:opacity-50"
          >
            {loadingAi ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>Extraer Valores con IA</span>
          </button>

          {hasValues && (
            <div className="mt-4 sm:mt-auto flex items-center gap-2 ml-auto">
              <button
                onClick={handleCopyAllJson}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 rounded-md hover:bg-slate-50 transition"
              >
                {copiedJson ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedJson ? '¡JSON Copiado!' : 'Copiar JSON'}</span>
              </button>

              <button
                onClick={handleExportCsv}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 rounded-md hover:bg-slate-50 transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Exportar CSV</span>
              </button>
            </div>
          )}
        </div>

      </div>

      {/* Results Table */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-bold text-sm text-slate-900 dark:text-white">
            Valores Estructurados Extraídos
          </h4>
          {aiResult?.latency_seconds && (
            <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">
              ⚡ Latencia: {aiResult.latency_seconds} s • Páginas consultadas: [{aiResult.pages_consulted?.join(', ')}]
            </span>
          )}
        </div>

        <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-850 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 uppercase font-semibold">
                <th className="py-2.5 px-4 w-1/3">Campo</th>
                <th className="py-2.5 px-4 w-1/2">Valor Extraído</th>
                <th className="py-2.5 px-4 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {!hasValues ? (
                <tr>
                  <td colSpan="3" className="py-8 text-center text-slate-400">
                    Haz clic en "Extraer Valores con IA" para obtener los datos estructurados.
                  </td>
                </tr>
              ) : (
                Object.entries(values).map(([field, val]) => {
                  const isFound = val && val !== 'No encontrado' && !val.includes('Error');
                  const isCopied = copiedKey === field;

                  return (
                    <tr key={field} className="hover:bg-slate-50/70 dark:hover:bg-slate-850/50 transition">
                      <td className="py-2.5 px-4 font-semibold text-slate-800 dark:text-slate-200">
                        {field}
                      </td>
                      <td className="py-2.5 px-4">
                        <span className={`font-mono ${isFound ? 'text-slate-900 dark:text-white font-medium' : 'text-slate-400 italic'}`}>
                          {val}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <button
                          onClick={() => handleCopyValue(field, val)}
                          className="px-2.5 py-1 text-[11px] font-medium border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 rounded inline-flex items-center gap-1 text-slate-700 dark:text-slate-300 transition"
                        >
                          {isCopied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                          <span>{isCopied ? 'Copiado' : 'Copiar'}</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
