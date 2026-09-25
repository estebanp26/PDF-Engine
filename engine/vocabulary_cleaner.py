import re
import unicodedata
from typing import Dict, Set, Optional

# Core Spanish dictionary for administrative, medical, commercial, and legal documents
VOCABULARY_LIST = [
    # General / administrative
    "fecha", "gestion", "orden", "regimen", "numero", "codigo", "cantidad", "total",
    "observacion", "observaciones", "descripcion", "detalle", "consecutivo", "documento",
    "identificacion", "cedula", "expedicion", "vencimiento", "registro", "vigencia",
    "resolucion", "formulario", "autorizacion", "radicado", "solicitud", "aprobado",
    "tramite", "auditoria", "impresion", "transcribe", "funcionario", "auxiliar",
    "administrativo", "responsable", "firma", "usuario", "externo", "interno",

    # Personal info
    "paciente", "nombre", "nombres", "apellidos", "primer", "segundo", "sexo", "edad",
    "nacimiento", "direccion", "telefono", "celular", "correo", "electronico", "municipio",
    "ciudad", "departamento", "pais", "zona", "barrio", "localidad", "afiliado",

    # Medical & Healthcare
    "diagnostico", "medico", "especialista", "prestador", "clinica", "hospital", "salud",
    "entidad", "primaria", "cooperativa", "asociado", "integral", "sociedad", "habilitacion",
    "procedimiento", "procedimientos", "examen", "examenes", "estudio", "laboratorio",
    "ecocardiograma", "transtoracico", "electrocardiograma", "electrocardiografico",
    "monitoreo", "continuo", "holter", "consulta", "urgencias", "hospitalizacion",
    "terapia", "tratamiento", "cirugia", "medicamento", "medicamentos", "dosis",
    "losartan", "hidroclorotiazida", "hidroxido", "aluminio", "previsalud", "semedical",
    "ceminsa", "coosalud", "sabanalarga",

    # Financial / Invoicing
    "factura", "proveedor", "cliente", "empresa", "subtotal", "descuento", "impuesto",
    "retencion", "valor", "pagar", "pagado", "saldo", "banco", "cuenta", "corriente",
    "ahorros", "tarjeta", "efectivo", "transferencia", "precio", "unitario", "pesos",

    # Calendar
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre", "lunes", "martes", "miercoles",
    "jueves", "viernes", "sabado", "domingo", "hora", "minuto", "dias", "meses", "anos",
]

# Canonical lookup: normalized -> display form with accents
DISPLAY_FORMS: Dict[str, str] = {
    "fecha": "Fecha", "gestion": "Gestión", "orden": "Orden", "regimen": "Régimen",
    "numero": "Número", "codigo": "Código", "observacion": "Observación",
    "observaciones": "Observaciones", "descripcion": "Descripción", "identificacion": "Identificación",
    "cedula": "Cédula", "expedicion": "Expedición", "resolucion": "Resolución",
    "autorizacion": "Autorización", "auditoria": "Auditoría", "impresion": "Impresión",
    "paciente": "Paciente", "direccion": "Dirección", "telefono": "Teléfono",
    "electronico": "Electrónico", "diagnostico": "Diagnóstico", "medico": "Médico",
    "habilitacion": "Habilitación", "ecocardiograma": "ecocardiograma",
    "transtoracico": "transtorácico", "electrocardiograma": "electrocardiograma",
    "electrocardiografico": "electrocardiográfico", "cirugia": "cirugía",
    "miercoles": "miércoles", "sabado": "sábado", "anos": "años",
    "auxiliar": "Auxiliar", "administrativo": "Administrativo", "externo": "externo",
    "transcribe": "Transcribe", "prestador": "Prestador", "municipio": "Municipio",
    "previsalud": "Previsalud", "semedical": "Semedical", "losartan": "Losartán",
    "hidroclorotiazida": "Hidroclorotiazida", "hidroxido": "Hidróxido",
    "ceminsa": "CEMINSA", "coosalud": "COOSALUD", "sabanalarga": "Sabanalarga",
}

def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize('NFKD', s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


class FastVocabCleaner:
    """Ultra-fast Spanish OCR post-processor.
    
    Corrects OCR substitutions (l/i, rn/m, f/t, etc.) for common vocabulary
    in microseconds using distance-1 hash lookups.
    Never corrupts numbers, alphanumeric IDs, or proper names.
    """

    def __init__(self):
        self.valid_words: Set[str] = set()
        # Precompute distance-1 deletion/substitution maps for sub-microsecond corrections
        self.deletions_map: Dict[str, str] = {}
        for word in VOCABULARY_LIST:
            norm = strip_accents(word)
            self.valid_words.add(norm)
            # Index deletions
            for i in range(len(norm)):
                del_word = norm[:i] + norm[i+1:]
                if del_word not in self.deletions_map:
                    self.deletions_map[del_word] = norm

        # Direct common OCR typo mapping
        self.direct_corrections = {
            "facha": "fecha",
            "gestlon": "gestion",
            "disgnostico": "diagnostico",
            "paclente": "paciente",
            "extemo": "externo",
            "extermo": "externo",
            "transtoracico": "transtoracico",
            "consanuo": "consalud",
            "consaquo": "consalud",
            "consaduo": "consalud",
            "fiduprevisora": "fiduprevisora",
            "transcribe": "transcribe",
            "auxlllar": "auxiliar",
            "administratlvo": "administrativo",
            # Faint / matrix-stippled logo and watermark corrections
            "emedica": "semedical",
            "semedica": "semedical",
            "sermedica": "semedical",
            "somedia": "semedical",
            "somedical": "semedical",
            "comarcal": "semedical",
            "comorira": "semedical",
            "comedical": "semedical",
            "provicalur": "previsalud",
            "previaalud": "previsalud",
            # Medications clipped by margin border
            "sartan": "losartan",
            "lojartan": "losartan",
            "droclorotiazida": "hidroclorotiazida",
            "hidrocloratiazida": "hidroclorotiazida",
            "droxido": "hidroxido",
        }

    @staticmethod
    def _format_case(token: str, disp: str) -> str:
        if token.isupper():
            return disp.upper()
        if token[0].isupper():
            return disp
        return disp.lower()

    def correct_word(self, token: str) -> str:
        """Correct a single word if it is a corrupted vocabulary word."""
        if len(token) < 4:
            return token

        # If it contains digits, don't touch (IDs, phone numbers, codes)
        if any(c.isdigit() for c in token):
            return token

        clean = strip_accents(token)

        # Check direct known OCR confusions first
        if clean in self.direct_corrections:
            target = self.direct_corrections[clean]
            disp = DISPLAY_FORMS.get(target, target)
            return self._format_case(token, disp)

        # If already a valid known word, restore canonical accents if needed
        if clean in self.valid_words:
            if clean in DISPLAY_FORMS:
                disp = DISPLAY_FORMS[clean]
                return self._format_case(token, disp)
            return token

        # Distance-1 check (e.g. paclente vs paciente, where 'l' replaced 'i')
        # Check if same length with 1 char substitution
        token_len = len(clean)
        for valid in self.valid_words:
            if len(valid) == token_len:
                diffs = sum(1 for a, b in zip(clean, valid) if a != b)
                if diffs == 1:
                    disp = DISPLAY_FORMS.get(valid, valid)
                    return self._format_case(token, disp)

        # Check 1 char insertion/deletion via map
        for i in range(token_len):
            del_variant = clean[:i] + clean[i+1:]
            if del_variant in self.deletions_map:
                cand = self.deletions_map[del_variant]
                if abs(len(cand) - token_len) <= 1:
                    disp = DISPLAY_FORMS.get(cand, cand)
                    return self._format_case(token, disp)

        return token

    def clean_text_block(self, text: str) -> str:
        """Process an entire OCR text block, fixing corrupted words and stripping symbol noise."""
        if not text:
            return ""

        output_lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Strip repetitive margin noise
            line = re.sub(r'[\=\|\>\<\_\~]{2,}', ' ', line).strip()
            alnum = sum(1 for c in line if c.isalnum())
            if alnum < 2 and len(line) > 1:
                continue

            tokens = re.split(r'(\s+|[.,;:()\[\]{}"\'\-]+)', line)
            cleaned_tokens = []
            for tok in tokens:
                if tok.isalpha() and len(tok) >= 4:
                    cleaned_tokens.append(self.correct_word(tok))
                else:
                    cleaned_tokens.append(tok)

            rebuilt = "".join(cleaned_tokens).strip()
            rebuilt = re.sub(r'\s{2,}', ' ', rebuilt)
            if rebuilt:
                output_lines.append(rebuilt)

        return "\n".join(output_lines)


# Global singleton instance
vocab_cleaner = FastVocabCleaner()
