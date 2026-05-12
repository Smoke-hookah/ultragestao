"""
Exemplo de uso do Orquestrador para casos de teste.
Execute: python exemplo_uso.py
"""

from services.orquestrador import Orquestrador
from utils.logger import logger


def exemplo_processamento_simples():
    """
    Exemplo 1: Processamento simples de planilha.
    """
    logger.info("="*70)
    logger.info("EXEMPLO 1: Processamento Simples")
    logger.info("="*70)
    
    orq = Orquestrador()
    
    # Processar planilha
    sucesso, resultados = orq.processar_planilha(
        caminho_planilha="exemplo_de_planilha.xlsx",
        tipo_separacao="placa",  # ou "rota"
        baixar_pdf=True,
        baixar_xml=False
    )
    
    # Exibir resumo
    resumo = orq.obter_resumo()
    logger.info(f"\nResumo: {resumo['sucesso']}/{resumo['total_alocacoes']} sucesso")
    
    return sucesso, resultados


def exemplo_processamento_com_xml():
    """
    Exemplo 2: Processamento com download de XML.
    """
    logger.info("="*70)
    logger.info("EXEMPLO 2: Processamento com XML")
    logger.info("="*70)
    
    orq = Orquestrador()
    
    # Processar planilha
    sucesso, resultados = orq.processar_planilha(
        caminho_planilha="exemplo_de_planilha.xlsx",
        tipo_separacao="rota",  # Separar por rota
        baixar_pdf=True,
        baixar_xml=True,  # Também baixar XML
        # metodo_pdf="api" (padrão) | "local" (teste) | "api_fallback_local"
        # metodo_pdf="local",
    )
    
    # Exibir detalhes
    resumo = orq.obter_resumo()
    
    for resultado in resumo['resultados'][:3]:  # Primeiros 3
        logger.info(f"\nChave: {resultado['chave']}")
        logger.info(f"  Sucesso: {resultado['sucesso']}")
        logger.info(f"  Etapa: {resultado['etapa']}")
        logger.info(f"  PDF: {resultado['arquivo_pdf']}")
        logger.info(f"  XML: {resultado['arquivo_xml']}")
    
    return sucesso, resultados


if __name__ == '__main__':
    try:
        # Executar exemplos
        print("\n🚀 Exemplos de Uso\n")
        
        # Descomente para executar:
        # exemplo_processamento_simples()
        # exemplo_processamento_com_xml()
        
        logger.info("\n✓ Exemplos prontos para uso")
        logger.info("Descomente as funções desejadas em exemplo_uso.py")
        
    except Exception as e:
        logger.error(f"Erro: {e}")
