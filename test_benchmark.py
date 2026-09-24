#!/usr/bin/env python3
"""
test_benchmark.py
Creates a realistic 20-page test PDF combining:
- Digital text (invoices, corporate reports, contracts)
- Embedded images with text & numbers
- Low-contrast / noisy scanned pages to test the 'Anti-Todo' OCR
Then runs the full PDF-Engine pipeline, measures exact speeds, and tests search + AI.

Run:  .venv/bin/python3 test_benchmark.py
"""

import os
import sys
import io
import time
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import asyncio

from engine.pdf_reader import PDFEngineReader
from engine.search_index import SearchEngine
from engine.ai_extractor import AIExtractor

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(HERE, "samples", "benchmark_20_pages.pdf")

FONT_PATH = "/usr/share/fonts/noto/NotoSans-Regular.ttf"

def get_font(size=28):
    if os.path.exists(FONT_PATH):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()

def generate_sample_image(text_lines, width=900, height=600, noisy=False, low_contrast=False) -> bytes:
    """Generates an image containing text, with realistic font size and optional noise."""
    bg_color = (225, 220, 210) if low_contrast else (255, 255, 255)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    font = get_font(32)

    y = 50
    text_color = (90, 85, 80) if low_contrast else (20, 20, 20)

    for line in text_lines:
        draw.text((50, y), line, fill=text_color, font=font)
        y += 65

    if noisy:
        pixels = img.load()
        for _ in range(4000):
            rx = random.randint(0, width - 1)
            ry = random.randint(0, height - 1)
            val = random.choice([40, 200])
            pixels[rx, ry] = (val, val, val)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def build_20_page_benchmark_pdf(output_path: str):
    """Builds a realistic 20-page test PDF."""
    print(f"[*] Generando PDF de prueba de 20 páginas en: {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = fitz.open()

    for i in range(1, 13):
        page = doc.new_page(width=595, height=842)  # A4
        if i == 1:
            content = (
                "DOCUMENTO MAESTRO DE OPERACIONES Y SERVICIOS - RIWI TECH\n\n"
                "Fecha de Emisión: 23 de Septiembre de 2026\n"
                "Proveedor Autorizado: Innovaciones Digitales del Norte S.A.S.\n"
                "NIT: 901.458.789-3\n"
                "Número de Factura: FACT-2026-8849\n"
                "Valor Total a Pagar: $45.850.000 COP\n"
                "Responsable: Andres Teheran - Director de Operaciones\n"
                "Estado: Aprobado para desembolso inmediato.\n\n"
                "Términos y condiciones aplicables según el acuerdo marco de telecomunicaciones y software."
            )
        elif i == 5:
            content = (
                f"REPORTE FINANCIERO TRIMESTRAL - PÁGINA {i}\n\n"
                "Palabra Clave de Prueba: CÓDIGO_SECRETO_ALFA_99\n"
                "Detalle de cuentas por pagar a proveedores estratégicos.\n"
                "Presupuesto asignado al departamento de Inteligencia Artificial: $120.000 USD.\n"
                "Meta de automatización de buzón: 95% de correos clasificados sin intervención manual."
            )
        else:
            content = (
                f"SECCIÓN TÉCNICA Y NORMATIVA CORPORATIVA - PÁGINA {i}\n\n"
                "Este documento describe los protocolos de gobernanza de datos y procesamiento de archivos.\n"
                f"Parágrafo {i}.1: Todos los sistemas deberán cumplir con tiempos de respuesta sub-segundo.\n"
                "La arquitectura se basa en microservicios y procesamiento distribuido de documentos.\n"
                "Se garantiza la trazabilidad total mediante identificadores únicos de transacción.\n"
                f"Hash de control de integridad: 8fbc4920e{i}a7b6c5d4e3f2a1b0c9d8e7f6."
            )
        page.insert_text((50, 70), content, fontsize=12)

    image_specs = [
        ["RECIBO DE CAJA MENOR #4491", "Fecha: 15/09/2026", "Valor: $750.000 COP", "PalabraClave: TICKET_IMAGEN_EMBEBIDA"],
        ["ORDEN DE COMPRA OC-9920", "Solicitante: Soporte Tecnico", "Aprobado por: Gerencia General"],
        ["CERTIFICADO DE RETENCION EN LA FUENTE", "Año Gravable: 2026", "Base Gravable: $38.000.000 COP"],
        ["SELLO DE AUDITORIA INTERNA", "Estado: VERIFICADO Y CONFORME", "Inspector: Dilan Chavez"]
    ]
    for idx, lines in enumerate(image_specs, start=13):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), f"Página {idx}: Documento con Imagen Adjunta", fontsize=12)
        img_bytes = generate_sample_image(lines, width=800, height=450, noisy=False)
        rect = fitz.Rect(50, 100, 545, 450)
        page.insert_image(rect, stream=img_bytes)

    scanned_specs = [
        ["FACTURA ESCANEADA ANTIGUA #7721", "Proveedor: Suministros Industriales", "Total: $12.300.000", "PalabraClave: ESCANEO_RUIDOSO_DETECTADO"],
        ["ACTA DE ENTREGA DE EQUIPOS", "Servidor Dell PowerEdge", "Responsable de Entrega: Esteban Padilla"],
        ["PAGARE EN BLANCO Y CARTA DE INSTRUCCIONES", "Deudor Principal: Consorcio Caribe", "Ciudad: Barranquilla"],
        ["CONSTANCIA DE CUMPLIMIENTO AMBIENTAL", "Norma ISO 14001:2015", "Vigencia: 2026-2028"]
    ]
    for idx, lines in enumerate(scanned_specs, start=17):
        page = doc.new_page(width=595, height=842)
        # No digital text, only the noisy image filling the page
        img_bytes = generate_sample_image(lines, width=900, height=1200, noisy=True, low_contrast=True)
        rect = fitz.Rect(20, 20, 575, 822)  # 88.8% del área → dedups como escaneo de página completa
        page.insert_image(rect, stream=img_bytes)

    doc.save(output_path)
    doc.close()
    print(f"[✓] PDF de 20 páginas creado exitosamente ({os.path.getsize(output_path) / 1024:.1f} KB).")


async def _pick_qwen_model(ai: AIExtractor) -> str:
    """Elija el primer modelo qwen disponible (fallback a qwen2.5:1.5b)."""
    try:
        models = await ai.list_available_models()
        qwen = [m for m in models if "qwen" in m.lower()]
        if qwen:
            return qwen[0]
    except Exception:
        pass
    return "qwen2.5:1.5b"


async def run_speed_test(pdf_path: str):
    """Executes benchmark and prints detailed telemetry in spec format."""
    print("\n" + "=" * 70)
    print("BENCHMARK PDF-ENGINE (PyMuPDF + OCR + Índice + Qwen 2.5)")
    print("=" * 70)

    reader = PDFEngineReader()

    t0 = time.perf_counter()
    doc_data = reader.process_pdf(pdf_path, run_ocr_on_images=True)
    total_doc_time = time.perf_counter() - t0
    metrics = doc_data["metrics"]

    digital_pages = sum(1 for p in doc_data["pages"] if not p["is_scanned"] and p["text"].strip())
    ocr_pages = sum(1 for p in doc_data["pages"] if p["is_scanned"])
    total_chars = sum(len(p["text"]) for p in doc_data["pages"]) + \
                  sum(len(p.get("ocr_text", "")) for p in doc_data["pages"])

    print("\n[ETAPA 1: LECTURA PyMuPDF + OCR paralelo]")
    print(f" • Páginas digitales (sin OCR): {digital_pages}")
    print(f" • Páginas/ítems escaneados (OCR, sin duplicar): {doc_data['ocr_items_processed']}")
    print(f" • Tiempo total lectura+OCR: {total_doc_time:.3f} s ({total_doc_time*1000:.1f} ms)")
    print(f" • Velocidad: {metrics['pages_per_second']} páginas/segundo")
    print(f" • Desglose:")
    for k, v in metrics["breakdown"].items():
        print(f"     - {k}: {v:.4f} s ({v*1000:.1f} ms)")

    print("\n[ETAPA 2: ÍNDICE DE BÚSQUEDA PRECONSTRUIDO]")
    si = doc_data.get("search_index") or {}
    word_locations = si.get("word_locations", {})
    print(f" • Palabras indexadas: {len(word_locations):,}")
    print(f" • Construido durante la lectura (incluido en el tiempo de la Etapa 1).")

    print("\n[ETAPA 3: BÚSQUEDA DE PALABRAS CLAVE]")
    test_queries = [
        "FACTURA",
        "CÓDIGO_SECRETO_ALFA_99",
        "TICKET_IMAGEN_EMBEBIDA",
        "ESCANEO_RUIDOSO_DETECTADO",
        "Andres Teheran",
    ]
    search_times = []
    for q in test_queries:
        t_s = time.perf_counter()
        res = SearchEngine.search(doc_data, q)
        t_search = time.perf_counter() - t_s
        search_times.append(t_search * 1000)
        print(f" • '{q}' | Hits: {res['total_matches']} | Páginas: {res['matched_pages']} | {t_search*1000:.2f} ms")
        for r in res["results"][:2]:
            print(f"     -> [{r['source_label']}] pág {r['page']} ({r['match_type']}): {r['snippet'][:70]}")
    print(f" • Media de tiempo por búsqueda: {sum(search_times)/len(search_times):.2f} ms")

    print("\n[ETAPA 4: EXTRACCIÓN CON IA (Qwen 2.5)]")
    ai = AIExtractor()
    model = await _pick_qwen_model(ai)
    target_fields = ["Número de Factura", "Proveedor Autorizado", "NIT", "Valor Total a Pagar", "Responsable"]

    t_ai_start = time.perf_counter()
    ai_result = await ai.extract_values(doc_data, target_fields, model=model)
    t_ai_total = time.perf_counter() - t_ai_start

    print(f" • Modelo: {ai_result['model_used']}")
    print(f" • Tiempo de inferencia IA: {ai_result['latency_seconds']:.3f} s ({ai_result['latency_ms']} ms)")
    print(f" • Páginas consultadas: {ai_result['pages_consulted']}")
    if ai_result.get("error"):
        print(f" • ⚠ Error IA: {ai_result['error']}")
    for k, v in ai_result["values"].items():
        print(f"     - {k}: {v}")

    grand_total = total_doc_time + t_ai_total
    print("\n" + "=" * 70)
    print(f"RESUMEN: Lectura 20 págs | digital={digital_pages} | OCR={ocr_pages} | chars={total_chars}")
    print(f"PyMuPDF+OCR+Índice = {total_doc_time:.3f}s | IA = {t_ai_total:.3f}s")
    print(f"TIEMPO TOTAL DEL SISTEMA COMPLETO: {grand_total:.3f} SEGUNDOS")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    if os.path.exists(SAMPLE_PATH):
        os.remove(SAMPLE_PATH)
    build_20_page_benchmark_pdf(SAMPLE_PATH)
    asyncio.run(run_speed_test(SAMPLE_PATH))