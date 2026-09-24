#!/usr/bin/env python3
"""
benchmark_ocr_tuning.py
Barrido de configuración OCR para elegir el mejor equilibrio rendimiento/precisión:
  1. Workers del pool paralelo:       [1, 2, 4, 6, 8, 12]
  2. DPI de render de páginas:         [100, 150, 175, 200, 250]

Usa un escaneo real (página completa) generado por test_benchmark. Tesseract debe
estar instalado; si no, el script lo detecta y aborta con un mensaje claro.

Run:  .venv/bin/python3 benchmarks/benchmark_ocr_tuning.py [--dpi-only]
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil

if shutil.which("tesseract") is None:
    sys.exit("Tesseract no está instalado. Instálalo para ejecutar el barrido OCR (sudo apt install tesseract-ocr tesseract-ocr-spa).")

from test_benchmark import build_20_page_benchmark_pdf, SAMPLE_PATH
from engine.pdf_reader import PDFEngineReader

WORKERS_GRID = [1, 2, 4, 6, 8, 12]
DPI_GRID = [100, 150, 175, 200, 250]


def bench(workers: int, dpi: int, pdf_path: str) -> dict:
    reader = PDFEngineReader(ocr_workers=workers)
    t0 = time.perf_counter()
    doc = reader.process_pdf(pdf_path, run_ocr_on_images=True, dpi=dpi)
    elapsed = time.perf_counter() - t0
    return {
        "workers": workers,
        "dpi": dpi,
        "seconds": round(elapsed, 3),
        "ocr_items": doc["ocr_items_processed"],
        "cache_hit": doc["cached"],
    }


def main():
    dpi_only = "--dpi-only" in sys.argv
    if not os.path.exists(SAMPLE_PATH):
        build_20_page_benchmark_pdf(SAMPLE_PATH)

    best_total = None

    # Barrido de workers con DPI fijo (150)
    if not dpi_only:
        print(f"\n{'WORKERS':<9}{'DPI':<6}{'TIEMPO(s)':<12}{'ÍTEMS OCR':<10}{'CACHE'}")
        print("-" * 48)
        for w in WORKERS_GRID:
            r = bench(w, 150, SAMPLE_PATH)
            if best_total is None or r["seconds"] < best_total["seconds"]:
                best_total = r
            print(f"{w:<9}{150:<6}{r['seconds']:<12.3f}{r['ocr_items']:<10}{r['cache_hit']}")
        print(f"  → Mejor workers (DPI 150): {best_total['workers']} en {best_total['seconds']}s")

    # Barrido de DPI con el mejor workers (o 6 por defecto)
    best_workers = best_total["workers"] if best_total else 6
    print(f"\n{'DPI':<6}{'WORKERS':<9}{'TIEMPO(s)':<12}{'ÍTEMS OCR':<10}")
    print("-" * 44)
    best_dpi = None
    for dpi in DPI_GRID:
        r = bench(best_workers, dpi, SAMPLE_PATH)
        if best_dpi is None or r["seconds"] < best_dpi["seconds"]:
            best_dpi = r
        print(f"{dpi:<6}{best_workers:<9}{r['seconds']:<12.3f}{r['ocr_items']:<10}")
    print(f"  → Mejor DPI (workers={best_workers}): {best_dpi['dpi']} en {best_dpi['seconds']}s")

    print(f"\nConfiguración recomendada: workers={best_dpi['workers']}, dpi={best_dpi['dpi']}")


if __name__ == "__main__":
    main()