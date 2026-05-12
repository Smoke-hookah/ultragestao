"""Diagnóstico: extrai e exibe o texto cru de cada pagina dos PDFs de boletos."""
import sys
import os
import tempfile
from pathlib import Path

# Adiciona o raiz do projeto no path
sys.path.insert(0, str(Path(__file__).parent))

from pypdf import PdfReader, PdfWriter

PDFS = [
    r"C:\Users\feito\Documents\Project\UltraDanfeXML\output\BOLETO 06-05 SP.pdf",
    r"C:\Users\feito\Documents\Project\UltraDanfeXML\output\BOLETO 06-05 RJ.pdf",
    r"C:\Users\feito\Documents\Project\UltraDanfeXML\output\BOLETO 06-05 MG.pdf",
]

MAX_PAGINAS = 3  # analisa até 3 páginas de cada PDF


def extrair_docling(pdf_path: str, page_index: int) -> str:
    try:
        import logging
        from docling.document_converter import DocumentConverter
        logging.getLogger("RapidOCR").setLevel(logging.ERROR)
        logging.getLogger("rapidocr").setLevel(logging.ERROR)
        logging.getLogger("docling").setLevel(logging.ERROR)

        reader = PdfReader(pdf_path)
        converter = DocumentConverter()
        with tempfile.TemporaryDirectory(prefix="diag_docling_") as tmpdir:
            pagina_pdf = Path(tmpdir) / f"pagina_{page_index}.pdf"
            writer = PdfWriter()
            writer.add_page(reader.pages[page_index])
            with open(pagina_pdf, "wb") as f:
                writer.write(f)
            result = converter.convert(pagina_pdf)
            doc = getattr(result, "document", None)
            if not doc:
                return "(docling: sem documento)"
            texto = ""
            if hasattr(doc, "export_to_text"):
                texto = doc.export_to_text() or ""
            if not texto and hasattr(doc, "export_to_markdown"):
                texto = doc.export_to_markdown() or ""
            return texto or "(docling: vazio)"
    except Exception as e:
        return f"(docling erro: {e})"


def main():
    saida = Path("diagnostico_boletos_output.txt")
    linhas = []

    for pdf_path in PDFS:
        p = Path(pdf_path)
        if not p.exists():
            linhas.append(f"\n{'='*70}")
            linhas.append(f"ARQUIVO NAO ENCONTRADO: {pdf_path}")
            continue

        reader = PdfReader(pdf_path)
        total = len(reader.pages)
        linhas.append(f"\n{'='*70}")
        linhas.append(f"PDF: {p.name}  ({total} paginas total)")
        linhas.append(f"{'='*70}")

        for idx in range(min(MAX_PAGINAS, total)):
            linhas.append(f"\n--- Pagina {idx+1} ---")

            # pypdf
            try:
                texto_pypdf = reader.pages[idx].extract_text() or "(pypdf: vazio)"
            except Exception as e:
                texto_pypdf = f"(pypdf erro: {e})"

            linhas.append(f"\n[pypdf]")
            linhas.append(repr(texto_pypdf))

            # Docling
            print(f"  Extraindo Docling: {p.name} pag {idx+1}...", flush=True)
            texto_docling = extrair_docling(pdf_path, idx)
            linhas.append(f"\n[Docling]")
            linhas.append(repr(texto_docling))

    conteudo = "\n".join(linhas)
    saida.write_text(conteudo, encoding="utf-8")
    print(f"\nSalvo em: {saida.resolve()}")
    print("\n" + conteudo[:8000])  # exibe os primeiros 8000 chars no console


if __name__ == "__main__":
    main()
