"""Script principal para CLI e execução direta."""

import sys
import argparse
import multiprocessing
import os
from pathlib import Path

from utils.logger import logger
from services.orquestrador import Orquestrador


def processar_via_cli():
    """Processa planilhas via linha de comando."""
    parser = argparse.ArgumentParser(
        description='Processador de Planilhas de Alocação - API Meu Danfe'
    )
    
    parser.add_argument(
        'planilha',
        nargs='?',
        default=None,
        help='Caminho da planilha Excel (.xlsx)'
    )
    
    parser.add_argument(
        '--tipo-separacao',
        choices=['placa', 'rota'],
        default='placa',
        help='Como separar os arquivos (padrão: placa)'
    )
    
    parser.add_argument(
        '--pdf',
        action='store_true',
        default=True,
        help='Baixar PDF (padrão: True)'
    )
    
    parser.add_argument(
        '--xml',
        action='store_true',
        default=False,
        help='Baixar XML (padrão: False)'
    )

    parser.add_argument(
        '--metodo-pdf',
        choices=['api', 'local', 'api_fallback_local'],
        default='api',
        help="Como obter PDF: api (padrão), local (teste), api_fallback_local"
    )

    parser.add_argument(
        '--pasta-xmls',
        default=None,
        help='Pasta contendo os XMLs para vincular por chave (necessário para metodo_pdf=local)'
    )
    
    parser.add_argument(
        '--api',
        action='store_true',
        help='Iniciar servidor API em vez de processar'
    )
    
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Iniciar interface gráfica com seletor de arquivos'
    )
    
    args = parser.parse_args()
    
    # Se --gui, iniciar interface gráfica
    if args.gui:
        logger.info("🖥️  Iniciando interface gráfica...")
        from interface_grafica import interface_principal
        interface_principal()
        return
    
    # Se --api, iniciar servidor
    if args.api:
        logger.info("🌐 Iniciando servidor API...")
        os.environ.setdefault(
            "ULTRADANFE_PLAYWRIGHT_BROWSERS_DIR",
            str(Path(__file__).resolve().parent / "playwright-browsers"),
        )
        from api import app
        app.run(debug=False, host='0.0.0.0', port=5000)
        return
    
    # Processar planilha
    if args.planilha is None:
        logger.error("❌ Nenhuma planilha foi fornecida")
        sys.exit(1)
    
    caminho = Path(args.planilha)
    
    if not caminho.exists():
        logger.error(f"❌ Arquivo não encontrado: {caminho}")
        sys.exit(1)
    
    logger.info(f"📊 Processando: {caminho}")
    logger.info(f"📍 Tipo de separação: {args.tipo_separacao}")
    logger.info(f"📥 PDF: {args.pdf}, XML: {args.xml}, método PDF: {args.metodo_pdf}")
    
    # Executar
    orq = Orquestrador()
    sucesso, resultados = orq.processar_planilha(
        str(caminho),
        args.tipo_separacao,
        args.pdf,
        args.xml,
        metodo_pdf=args.metodo_pdf,
        pasta_xmls=args.pasta_xmls,
    )
    
    # Exibir resumo
    resumo = orq.obter_resumo()
    
    print("\n" + "="*70)
    print("RESUMO DO PROCESSAMENTO")
    print("="*70)
    print(f"Total de alocações: {resumo['total_alocacoes']}")
    print(f"Sucesso: {resumo['sucesso']}")
    print(f"Erros: {resumo['erros']}")
    print(f"Taxa de sucesso: {resumo['taxa_sucesso']}")
    print("="*70)
    
    # Detalhes
    if resumo['total_alocacoes'] <= 20:
        print("\nDETALHES:")
        for r in resumo['resultados']:
            status = "✓" if r['sucesso'] else "✗"
            print(f"{status} {r['chave']}: {r['mensagem']}")
    else:
        print(f"\nPrimeiras 10 de {resumo['total_alocacoes']} resultados:")
        for r in resumo['resultados'][:10]:
            status = "✓" if r['sucesso'] else "✗"
            print(f"{status} {r['chave']}: {r['mensagem']}")
    
    print("="*70)
    
    # Retornar código de saída
    sys.exit(0 if sucesso else 1)


if __name__ == '__main__':
    try:
        multiprocessing.freeze_support()
        processar_via_cli()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Processamento cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)
