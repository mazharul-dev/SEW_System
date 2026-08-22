from __future__ import annotations

from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from .paths import MODEL_TEST_DIR, PROOFREADER_DIR, TABLE_CONVERTER_DIR


@lru_cache(maxsize=None)
def load_module(module_name: str, file_path: str) -> ModuleType:
    path = Path(file_path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def parse_docx_bytes(data: bytes) -> dict:
    module = load_module("integrated_mcq_proofreader_parser", str(PROOFREADER_DIR / "app" / "parser.py"))
    return module.parse_docx_bytes(data)


def convert_table_docx(stream, subject: str):
    module = load_module("integrated_table_docx_converter", str(TABLE_CONVERTER_DIR / "docx_converter.py"))
    return module.convert_docx(stream, subject)


def clean_model_test_docx(input_path: str, output_path: str, **options) -> str:
    module = load_module(
        "integrated_model_test_docx_cleaner",
        str(MODEL_TEST_DIR / "processor" / "docx_cleaner.py"),
    )
    return module.process_docx_document(input_path, output_path, **options)
