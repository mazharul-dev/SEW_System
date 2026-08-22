from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
MODULES_DIR = BASE_DIR / "modules"

MAZHARUL_CONVERTER_DIR = MODULES_DIR / "mazharul-converter"
MODEL_TEST_DIR = MODULES_DIR / "Model_Test_zip_source" / "Model_Test"
PROOFREADER_DIR = MODULES_DIR / "MCQ_Proofreader"
TABLE_CONVERTER_DIR = MODULES_DIR / "Unstructured-DOCX-to-Structured-Table-Based-Converter"
