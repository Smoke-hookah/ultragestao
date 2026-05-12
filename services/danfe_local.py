"""Geracao local de DANFE em PDF."""

from __future__ import annotations

import os
import tempfile
import warnings
from pathlib import Path
from typing import Callable, Optional


warnings.filterwarnings("ignore", message='.*has no "viewBox".*')

_BRAZIL_DANFE_CLASS = None
_BRAZIL_DANFE_IMPORT_ERROR: Optional[str] = None
_GENERIC_MODULE = None
_GENERIC_IMPORT_ERRORS: list[str] | None = None


class DanfeLocalError(RuntimeError):
    pass


def _try_call_writer(func: Callable, xml_string: str, out_path: str) -> bool:
    try:
        func(xml_string, out_path)
        return True
    except TypeError:
        try:
            func(xml_string, destino=out_path)
            return True
        except TypeError:
            try:
                func(xml=xml_string, destino=out_path)
                return True
            except TypeError:
                return False


def _get_brazil_danfe_class():
    global _BRAZIL_DANFE_CLASS, _BRAZIL_DANFE_IMPORT_ERROR

    if _BRAZIL_DANFE_CLASS is not None:
        return _BRAZIL_DANFE_CLASS
    if _BRAZIL_DANFE_IMPORT_ERROR is not None:
        raise DanfeLocalError(_BRAZIL_DANFE_IMPORT_ERROR)

    try:
        from brazilfiscalreport.danfe.danfe import Danfe as BrazilDanfe

        _BRAZIL_DANFE_CLASS = BrazilDanfe
        return _BRAZIL_DANFE_CLASS
    except Exception as exc:
        _BRAZIL_DANFE_IMPORT_ERROR = (
            "Biblioteca de DANFE local nao encontrada. "
            "Instale com: pip install brazilfiscalreport. "
            f"Erro: {exc}"
        )
        raise DanfeLocalError(_BRAZIL_DANFE_IMPORT_ERROR) from exc


def _get_generic_danfe_module():
    global _GENERIC_MODULE, _GENERIC_IMPORT_ERRORS

    if _GENERIC_MODULE is not None:
        return _GENERIC_MODULE
    if _GENERIC_IMPORT_ERRORS is not None:
        return None

    import_errors: list[str] = []
    for mod_name in ("gerador_danfe", "gerador_danfe.danfe", "danfe"):
        try:
            _GENERIC_MODULE = __import__(mod_name, fromlist=["*"])
            _GENERIC_IMPORT_ERRORS = import_errors
            return _GENERIC_MODULE
        except Exception as exc:
            import_errors.append(f"{mod_name}: {exc}")

    _GENERIC_IMPORT_ERRORS = import_errors
    return None


def escolher_executor_local_pdf(total_items: int) -> tuple[str, int]:
    """Escolhe automaticamente thread ou process para lotes locais."""
    requested = (os.getenv("LOCAL_PDF_EXECUTOR") or "auto").strip().lower()
    if requested not in {"auto", "thread", "process"}:
        requested = "auto"

    cpu = os.cpu_count() or 4
    if requested == "auto":
        requested = "process" if cpu > 1 and total_items >= max(24, cpu * 4) else "thread"

    workers_env = (os.getenv("LOCAL_PDF_WORKERS") or "").strip()
    if workers_env.isdigit():
        workers = int(workers_env)
    elif requested == "process":
        workers = min(cpu, 8)
    else:
        workers = min(cpu * 4, 32)

    if requested == "process":
        workers = min(workers, max(cpu, 1))
    else:
        workers = min(workers, 64)

    workers = max(1, workers)
    return requested, workers


def _parece_xml_nfe_renderizavel(xml_string: str) -> bool:
    texto = str(xml_string or "").strip().lower()
    if not texto:
        return False
    if "<retinutnfe" in texto or "<inutnfe" in texto:
        return False
    if "<proceventonfe" in texto or "<evento" in texto:
        return False
    return (
        "<infnfe" in texto
        or "<nfeproc" in texto
        or "<nfe " in texto
        or "<nfe>" in texto
    )


def gerar_pdf_danfe_bytes(xml_string: str) -> bytes:
    """Gera DANFE em PDF a partir do XML e retorna os bytes."""
    if not (xml_string or "").strip():
        raise DanfeLocalError("XML vazio para geracao local")
    if not _parece_xml_nfe_renderizavel(xml_string):
        raise DanfeLocalError("XML nao parece ser uma NF-e renderizavel para DANFE")

    brazil_error: Optional[str] = None

    try:
        danfe_class = _get_brazil_danfe_class()
        danfe = danfe_class(xml_string)
        pdf_bytes = danfe.output()
        if isinstance(pdf_bytes, bytearray):
            pdf_bytes = bytes(pdf_bytes)
        if not isinstance(pdf_bytes, bytes) or len(pdf_bytes) == 0:
            raise DanfeLocalError("Geracao local executou, mas o PDF retornou vazio")
        return pdf_bytes
    except DanfeLocalError as exc:
        brazil_error = str(exc)
    except Exception as exc:
        brazil_error = f"Falha no renderizador BrazilFiscalReport: {exc}"

    module = _get_generic_danfe_module()
    if module is None:
        errors = ", ".join(_GENERIC_IMPORT_ERRORS or [])
        if brazil_error:
            if errors:
                brazil_error = f"{brazil_error}. Tentativas de fallback: {errors}"
            raise DanfeLocalError(brazil_error)
        raise DanfeLocalError(
            "Biblioteca de DANFE local nao encontrada. "
            "Instale com: pip install brazilfiscalreport. "
            f"Tentativas de import: {errors}"
        )

    with tempfile.TemporaryDirectory(prefix="danfe_local_") as tmp:
        out_path = str(Path(tmp) / "danfe.pdf")

        for attr in ("gerar_danfe", "gerar_pdf", "generate_pdf", "danfe"):
            func = getattr(module, attr, None)
            if callable(func) and _try_call_writer(func, xml_string, out_path):
                pdf_path = Path(out_path)
                if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                    raise DanfeLocalError("Geracao local executou, mas o PDF nao foi criado")
                return pdf_path.read_bytes()

        for cls_name in ("Danfe", "DANFE"):
            cls = getattr(module, cls_name, None)
            if not cls:
                continue
            try:
                obj = cls(xml_string)
            except Exception:
                try:
                    obj = cls(xml=xml_string)
                except Exception:
                    continue

            for method_name in ("gerar_pdf", "render", "save", "to_pdf"):
                method = getattr(obj, method_name, None)
                if not callable(method):
                    continue
                try:
                    method(out_path)
                    pdf_path = Path(out_path)
                    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                        raise DanfeLocalError("Geracao local executou, mas o PDF nao foi criado")
                    return pdf_path.read_bytes()
                except TypeError:
                    try:
                        method(destino=out_path)
                        pdf_path = Path(out_path)
                        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                            raise DanfeLocalError("Geracao local executou, mas o PDF nao foi criado")
                        return pdf_path.read_bytes()
                    except Exception:
                        continue
                except Exception:
                    continue

    if brazil_error:
        raise DanfeLocalError(brazil_error)

    raise DanfeLocalError(
        "Nao consegui identificar como gerar o PDF com a biblioteca instalada. "
        "Verifique a API do pacote de DANFE local em uso."
    )


def gerar_pdf_danfe_task(chave: str, xml_string: str) -> tuple[str, bool, Optional[bytes], str]:
    """Worker seguro para thread/process pool."""
    chave_str = str(chave).strip()
    if not (xml_string or "").strip():
        return chave_str, False, None, "XML ausente: nao e possivel gerar DANFE local"

    try:
        pdf_bytes = gerar_pdf_danfe_bytes(xml_string)
        return chave_str, True, pdf_bytes, "Processamento concluido com sucesso"
    except DanfeLocalError as exc:
        return chave_str, False, None, str(exc)
    except Exception as exc:
        return chave_str, False, None, f"Erro ao gerar DANFE local: {exc}"
