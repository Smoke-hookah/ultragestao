"""
Interface gráfica interativa para processamento de planilhas com XMLs
"""

import sys
from pathlib import Path

# Adiciona o diretório do projeto ao PATH
sys.path.insert(0, str(Path(__file__).parent))

from utils.ui import (
    selecionar_planilha,
    selecionar_ou_usar_pasta_xmls_salva,
    confirmar_acao,
    mostrar_mensagem
)
from services.leitor_xml import LeitorXML
from utils.logger import logger


def interface_principal():
    """Interface principal interativa"""
    
    print("\n" + "="*60)
    print("🎯 ULTRA DANFE XML - Interface Gráfica")
    print("="*60 + "\n")
    
    try:
        # Passo 1: Selecionar Planilha
        print("📂 Selecionando planilha...")
        planilha = selecionar_planilha()
        
        if not planilha:
            mostrar_mensagem("Cancelado", "Nenhuma planilha foi selecionada.")
            return
        
        print(f"✓ Planilha: {Path(planilha).name}\n")
        
        # Passo 2: Selecionar Pasta de XMLs
        print("📁 Selecionando pasta com XMLs...")
        pasta_xmls = selecionar_ou_usar_pasta_xmls_salva()
        
        if not pasta_xmls:
            mostrar_mensagem("Cancelado", "Nenhuma pasta foi selecionada.")
            return
        
        print(f"✓ Pasta de XMLs: {pasta_xmls}\n")
        
        # Passo 3: Verificar XMLs (modo rápido)
        print("🔍 Verificando XMLs na pasta (modo rápido)...")
        leitor = LeitorXML(pasta_xmls)
        
        mapa, stats = leitor.carregar_mapa_chave_para_caminho()
        
        print(f"\n📊 RESUMO DE XMLs:")
        print(f"   Total: {stats['total']}")
        print(f"   ✓ Indexados: {stats['mapeadas']}")
        print(f"   ✗ Erros: {stats['erros']}")
        
        if stats['total'] == 0:
            mostrar_mensagem("Aviso", "Nenhum arquivo XML encontrado na pasta!")
            return
        
        # Passo 4: Selecionar opções de processamento
        print("\n" + "-"*60)
        print("⚙️ OPÇÕES DE PROCESSAMENTO:")
        print("-"*60)
        
        baixar_pdf = confirmar_acao(
            "Baixar PDFs",
            "Deseja baixar os PDFs correspondentes aos XMLs?"
        )

        metodo_pdf = "api"
        if baixar_pdf:
            usar_local = confirmar_acao(
                "Método de PDF (teste)",
                "Deseja gerar o DANFE em PDF localmente (modo teste, sem API)?\n\n"
                "Sim = Local (gerador-danfe)\nNão = API (padrão)"
            )
            metodo_pdf = "local" if usar_local else "api"
        
        baixar_xml = confirmar_acao(
            "Baixar XMLs",
            "Deseja também baixar cópias dos XMLs?"
        )
        
        criar_separacao = confirmar_acao(
            "Organizar por Placa/Rota",
            "Os arquivos serão organizados por Placa ou Rota?\n\n(Sim = Placa, Não = Rota)"
        )
        
        tipo_separacao = "placa" if criar_separacao else "rota"
        
        # Passo 5: Confirmação final
        print("\n" + "="*60)
        print("📋 RESUMO DA OPERAÇÃO:")
        print("="*60)
        print(f"Planilha: {Path(planilha).name}")
        print(f"Pasta XMLs: {pasta_xmls}")
        print(f"XMLs a processar: {resultado['processados']}/{resultado['total']}")
        print(f"Baixar PDF: {'Sim' if baixar_pdf else 'Não'}")
        print(f"Baixar XML: {'Sim' if baixar_xml else 'Não'}")
        print(f"Organizar por: {tipo_separacao.upper()}")
        print("="*60 + "\n")
        
        iniciar = confirmar_acao(
            "Iniciar Processamento",
            f"Iniciar processamento de {resultado['processados']} XMLs?"
        )
        
        if iniciar:
            # Aqui integra com o orquestrador
            from services.orquestrador import Orquestrador
            
            print("\n🚀 Iniciando processamento...\n")
            
            orq = Orquestrador()
            sucesso, alocacoes = orq.processar_planilha(
                caminho_planilha=planilha,
                pasta_xmls=pasta_xmls,
                tipo_separacao=tipo_separacao,
                baixar_pdf=baixar_pdf,
                baixar_xml=baixar_xml,
                metodo_pdf=metodo_pdf,
            )
            
            resumo = orq.obter_resumo()
            
            print("\n" + "="*60)
            print("✅ PROCESSAMENTO CONCLUÍDO")
            print("="*60)
            print(f"Total de registros: {resumo['total_alocacoes']}")
            print(f"✓ Sucesso: {resumo['sucesso']}")
            print(f"✗ Erros: {resumo['erros']}")
            print(f"Taxa de sucesso: {resumo['taxa_sucesso']}")
            print("="*60 + "\n")
            
            mostrar_mensagem(
                "Processamento Concluído",
                f"✓ {resumo['sucesso']} arquivos processados com sucesso\n"
                f"✗ {resumo['erros']} erro(s)\n\n"
                f"Taxa de sucesso: {resumo['taxa_sucesso']}%"
            )
        else:
            print("Operação cancelada.")
    
    except Exception as e:
        erro = f"Erro na execução: {str(e)}"
        logger.error(erro)
        mostrar_mensagem("Erro", erro, tipo='error')


if __name__ == "__main__":
    interface_principal()
