import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Sparkles, ArrowUpRight } from 'lucide-react';

export default function DropZone({ onFileSelected, onLoadBenchmark }) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
        onFileSelected(file);
      } else {
        alert('Por favor arrastra un archivo en formato PDF.');
      }
    }
  };

  const handleFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelected(file);
    }
  };

  return (
    <div className="max-w-3xl mx-auto my-12 px-4">
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        accept=".pdf"
        className="hidden"
      />

      {/* Drag & Drop Card */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-10 sm:p-14 text-center cursor-pointer transition-all duration-200 select-none ${
          isDragging
            ? 'border-blue-500 bg-blue-50/70 dark:bg-blue-950/40 ring-4 ring-blue-500/20 scale-[1.01]'
            : 'border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-blue-500 dark:hover:border-blue-500 hover:bg-slate-50/60 dark:hover:bg-slate-800/50 shadow-sm'
        }`}
      >
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition ${
            isDragging
              ? 'bg-blue-600 text-white'
              : 'bg-blue-50 dark:bg-blue-950/70 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/80'
          }`}>
            <UploadCloud className="w-8 h-8" />
          </div>

          <div className="space-y-1.5">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              {isDragging ? '¡Suelta tu archivo PDF aquí!' : 'Tira tu archivo PDF aquí'}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              o haz clic para seleccionar desde tu computadora
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2 pt-2 text-xs text-slate-400 dark:text-slate-500">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              <FileText className="w-3.5 h-3.5" />
              Documentos Digitales o Escaneados
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
              OCR y Extracción IA Automática
            </span>
          </div>
        </div>
      </div>

      {/* Alternative Demo Action */}
      {onLoadBenchmark && (
        <div className="mt-6 text-center">
          <button
            onClick={onLoadBenchmark}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition"
          >
            <span>¿No tienes un PDF a mano? Probar con el documento de benchmark (20 páginas)</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
