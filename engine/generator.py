import os
import io
import time
import random
from typing import List, Dict, Any, Optional
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

# AugLy imports
import augly.image as imaugs

FONT_PATH = "/usr/share/fonts/noto/NotoSans-Regular.ttf"

def get_font(size=26):
    if os.path.exists(FONT_PATH):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()

# Sample text paragraphs for dense pages
CORP_PARAGRAPHS = [
    "CLÁUSULA DE GOBERNANZA Y AUDITORÍA: Todos los procesos automatizados deberán ser trazables conforme a la norma ISO/IEC 27001. La supervisión periódica garantizará la integridad documental de cada transacción.",
    "REPORTE FINANCIERO Y LIQUIDACIÓN: Las facturas comerciales y órdenes de compra recibidas durante el periodo fiscal serán consolidadas en el libro mayor antes del cierre contable de medianoche.",
    "ESPECIFICACIONES TÉCNICAS DEL SISTEMA: El motor de procesamiento híbrido combina extracción a nivel C con un pool paralelo distribuido en los 12 núcleos del procesador AMD Ryzen para garantizar tiempos sub-segundo.",
    "ACTA DE RECEPCIÓN DE BIENES Y SERVICIOS: Se deja constancia de la entrega de equipos de telecomunicaciones, servidores blade y licencias de software corporativo en las sedes principales de Barranquilla y Bogotá.",
    "PROTOCOLO DE SEGURIDAD Y PRIVACIDAD DE DATOS: Ninguna credencial ni token de acceso será registrado en logs públicos. El cifrado en tránsito TLS 1.3 y en reposo AES-256 es de obligatorio cumplimiento."
]

def generate_augmented_image(
    text_lines: List[str],
    degradation: str = "mixed_all",
    width: int = 850,
    height: int = 500
) -> bytes:
    """Generates an image with text and applies AugLy transformations."""
    base_bg = (245, 245, 240) if degradation in ["scanned_noise", "low_contrast", "mixed_all"] else (255, 255, 255)
    img = Image.new("RGB", (width, height), color=base_bg)
    draw = ImageDraw.Draw(img)
    font = get_font(28)

    y = 50
    text_color = (60, 60, 60) if degradation in ["low_contrast", "scanned_noise"] else (20, 20, 20)

    for line in text_lines:
        draw.text((45, y), line, fill=text_color, font=font)
        y += 55

    # Apply AugLy transforms based on user choice
    try:
        if degradation == "scanned_noise":
            # AugLy Noise + Blur
            img = imaugs.random_noise(img, var=0.015)
            img = imaugs.blur(img, radius=0.8)
        elif degradation == "low_contrast":
            # AugLy Contrast & Brightness attenuation
            img = imaugs.contrast(img, factor=0.55)
            img = imaugs.brightness(img, factor=0.85)
        elif degradation == "skew_perspective":
            # AugLy Perspective / Skew
            img = imaugs.perspective_transform_and_shake(img, sigma=5)
        elif degradation == "mixed_all":
            # Combination: slight noise, JPEG compression artifacts, and contrast shift
            choice = random.choice(["noise", "contrast", "blur", "quality"])
            if choice == "noise":
                img = imaugs.random_noise(img, var=0.01)
            elif choice == "contrast":
                img = imaugs.contrast(img, factor=0.6)
            elif choice == "blur":
                img = imaugs.blur(img, radius=0.6)
            elif choice == "quality":
                img = imaugs.encoding_quality(img, quality=40)
    except Exception as e:
        print(f"AugLy transform fallback: {e}")

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

class PDFGenerator:
    """Synthetic PDF Document Generator powered by Meta's AugLy."""

    @staticmethod
    def generate(
        output_dir: str,
        page_count: int = 20,
        text_density: str = "repleta",
        images_count: int = 4,
        degradation: str = "mixed_all",
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Creates a customizable multi-page PDF with realistic text density,
        embedded/scanned images augmented with AugLy, and injected search keywords.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        filename = f"augly_doc_{page_count}p_{timestamp}.pdf"
        output_path = os.path.join(output_dir, filename)

        doc = fitz.open()

        # Target keywords to inject
        custom_kws = keywords or ["HABLAR", "AHORA", "CODIGO_AUG_CONFIDENCIAL", "FACTURA_RAMDOM_770"]
        injected_positions = []

        # Determine which pages get images
        image_pages = set()
        if images_count > 0 and page_count > 0:
            step = max(1, page_count // images_count)
            for idx in range(1, images_count + 1):
                target_p = min(page_count, idx * step)
                image_pages.add(target_p)

        # Decide text repetition count based on density
        density_mult = 4 if text_density == "repleta" else (2 if text_density == "media" else 1)

        for p_num in range(1, page_count + 1):
            page = doc.new_page(width=595, height=842) # A4

            # Check if this page is purely scanned (e.g. 1 out of every 5 pages if degradation is active)
            is_full_page_scan = (p_num in image_pages and degradation in ["scanned_noise", "mixed_all"] and p_num % 2 == 0)

            # Pick a keyword to inject on this page if available
            kw_to_inject = None
            if custom_kws and (p_num % 3 == 1 or p_num == 1):
                kw_to_inject = custom_kws[(p_num - 1) % len(custom_kws)]

            if is_full_page_scan:
                # Generate full page noisy scan (pure image, no digital text)
                scan_lines = [
                    f"--- DOCUMENTO ESCANEADO ANTIGUO (PÁGINA {p_num}) ---",
                    f"EXPEDIENTE: EXP-2026-AUG-{p_num * 110}",
                    f"FECHA: {20 + (p_num % 8)}/09/2026",
                    "ESTADO: ARCHIVADO EN BODEGA DE DOCUMENTACIÓN"
                ]
                if kw_to_inject:
                    scan_lines.append(f"PALABRA_CLAVE: {kw_to_inject}")
                    injected_positions.append({"page": p_num, "term": kw_to_inject, "location": "Escaneo Completo AugLy"})

                img_bytes = generate_augmented_image(scan_lines, degradation=degradation, width=900, height=1200)
                rect = fitz.Rect(20, 20, 575, 822)
                page.insert_image(rect, stream=img_bytes)

            else:
                # Digital text page
                lines = [
                    f"INFORME TÉCNICO Y FINANCIERO CONTRATUAL - PÁGINA {p_num}",
                    f"Identificador del Documento: DOC-AUG-2026-{p_num:04d}",
                    f"Fecha de Auditoría: 23 de Septiembre de 2026\n"
                ]

                if p_num == 1:
                    lines.extend([
                        "DATOS DE FACTURACIÓN Y OPERACIONES:",
                        "Proveedor: Corporación de Servicios y Tecnología S.A.",
                        "NIT: 900.871.234-9",
                        "Número de Factura: FACT-AUG-9941",
                        "Valor Total a Pagar: $68.450.000 COP",
                        "Responsable: Andres Teheran - Director de Auditoría",
                        "Estado de Pago: Aprobado para emisión bancaria.\n"
                    ])

                if kw_to_inject:
                    lines.append(f"Término de Verificación: {kw_to_inject}\n")
                    injected_positions.append({"page": p_num, "term": kw_to_inject, "location": "Texto Digital"})

                # Add dense corporate paragraphs
                for _ in range(density_mult):
                    para = random.choice(CORP_PARAGRAPHS)
                    lines.append(para + "\n")

                text_content = "\n".join(lines)
                page.insert_text((45, 60), text_content, fontsize=10.5)

                # If this page also contains an embedded image
                if p_num in image_pages:
                    img_kws = [
                        f"COMPROBANTE ADJUNTO (AUG-{p_num})",
                        f"Monto: ${(p_num * 1250000):,} COP",
                        f"Aprobado por Control Interno"
                    ]
                    # Also test disjoint words like 'hablar' or 'ahora' inside image
                    if p_num % 2 == 1:
                        img_kws.append("Término Embebido: hablar ahora")
                        injected_positions.append({"page": p_num, "term": "hablar ahora", "location": "Imagen Embebida AugLy"})

                    img_bytes = generate_augmented_image(img_kws, degradation=degradation, width=700, height=350)
                    # Insert in lower half of page
                    rect = fitz.Rect(50, 480, 545, 780)
                    page.insert_image(rect, stream=img_bytes)

        doc.save(output_path)
        doc.close()

        file_size_kb = round(os.path.getsize(output_path) / 1024, 1)

        return {
            "success": True,
            "filename": filename,
            "file_path": output_path,
            "total_pages": page_count,
            "text_density": text_density,
            "images_count": images_count,
            "degradation": degradation,
            "file_size_kb": file_size_kb,
            "injected_keywords": injected_positions
        }
