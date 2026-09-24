import pytest
from engine.vocabulary_cleaner import vocab_cleaner


def test_vocab_corrections():
    cases = [
        ("Paclente", "Paciente"),
        ("Disgnostico", "Diagnóstico"),
        ("Facha", "Fecha"),
        ("Gestlon", "Gestión"),
        ("extemo", "externo"),
        ("transtorÁcico", "transtorácico"),
        ("CONSAÑUO", "CONSALUD"),
        ("Auxlllar", "Auxiliar"),
        ("Administratlvo", "Administrativo"),
    ]
    for raw, expected in cases:
        corrected = vocab_cleaner.correct_word(raw)
        assert corrected.lower() == expected.lower(), f"Expected {expected}, got {corrected} for {raw}"


def test_vocab_leaves_ids_and_names_intact():
    safe_words = [
        "1043448102",
        "881202",
        "895001",
        "21688267",
        "830.053.105-3",
        "ESTEBAN",
        "PADILLA",
        "SILVA",
        "YARELYS",
        "NAVARRO",
        "GUTIERREZ",
    ]
    for word in safe_words:
        assert vocab_cleaner.correct_word(word) == word


def test_clean_text_block():
    text = """Nombre Paclente: PADILLA SILVA ESTEBAN JOSE
Identificacion: CC - 1043448102
Facha de Gestlon: 2026-08-20
Disgnostico: ecocardiograma transtorAcico
Prestador: CONSAÑUO VILLA COUNTRY
"""
    cleaned = vocab_cleaner.clean_text_block(text)
    assert "Paciente" in cleaned
    assert "1043448102" in cleaned
    assert "Fecha" in cleaned
    assert "Gestión" in cleaned
    assert "Diagnóstico" in cleaned
    assert "CONSALUD" in cleaned
