"""Teste rapido: verifica se o OCR fallback agora extrai texto dos PDFs Bradesco."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from services.gestor_saida import GestorSaida

PDFS = [
    r"C:\Users\feito\Documents\Project\UltraDanfeXML\output\BOLETO 06-05 SP.pdf",
    r"C:\Users\feito\Documents\Project\UltraDanfeXML\output\BOLETO 06-05 MG.pdf",
    r"C:\Users\feito\Documents\Project\UltraDanfeXML\output\BOLETO 06-05 RJ.pdf",
]

gs = GestorSaida()

for pdf_path in PDFS:
    p = Path(pdf_path)
    if not p.exists():
        print(f"\n[ERRO] Nao encontrado: {pdf_path}")
        continue

    print(f"\n{'='*60}")
    print(f"Testando: {p.name}")
    print(f"{'='*60}")

    documentos, nao_identificadas = gs.extrair_documentos_boletos(str(p))

    total = len(documentos)
    com_nf = sum(1 for d in documentos if d.get("doc_digits"))
    sem_nf = len(nao_identificadas)
    
    print(f"Total documentos: {total}")
    print(f"Com doc_digits:   {com_nf}")
    print(f"Sem NF:           {sem_nf}")
    print()

    for i, doc in enumerate(documentos[:5]):  # mostra os 5 primeiros
        print(f"  Doc {i+1}: doc_digits={doc.get('doc_digits')!r}  "
              f"candidates={doc.get('doc_candidates')!r}  "
              f"pagador={doc.get('pagador')!r}  "
              f"cnpj={doc.get('pagador_cnpj')!r}")
