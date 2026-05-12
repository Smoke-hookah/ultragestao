"""
Módulo para interface gráfica de seleção de arquivos e pastas
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import json
import logging

from config import CONFIG_DIR

logger = logging.getLogger(__name__)

PREFS_FILE = CONFIG_DIR / "preferencias.json"


def garantir_diretorio_config():
    """Garante que o diretório de configuração existe"""
    PREFS_FILE.parent.mkdir(exist_ok=True)


def selecionar_planilha(diretorio_inicial=None):
    """
    Abre janela para selecionar planilha Excel
    
    Args:
        diretorio_inicial: Diretório para iniciar a busca
        
    Returns:
        str: Caminho completo do arquivo selecionado ou None
    """
    garantir_diretorio_config()
    
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal
    
    # Tenta usar o último diretório usado
    if diretorio_inicial is None:
        diretorio_inicial = str(Path.home() / "Documents")
    
    arquivo = filedialog.askopenfilename(
        title="Selecionar Planilha de Alocações",
        filetypes=[("Arquivos Excel", "*.xlsx *.xls"), ("Todos", "*.*")],
        initialdir=diretorio_inicial
    )
    
    root.destroy()
    
    if arquivo:
        logger.info(f"Planilha selecionada: {arquivo}")
        return arquivo
    
    return None


def selecionar_pasta_xmls():
    """
    Abre janela para selecionar pasta com XMLs
    
    Returns:
        str: Caminho da pasta ou None
    """
    garantir_diretorio_config()
    
    # Quando chamado de um servidor web (Flask), tkinter pode travar dependendo do thread.
    # Usamos subprocess para abrir o seletor em um processo separado.
    import sys
    import subprocess
    
    # Script Python inline que será executado em processo separado
    script = '''
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)  # Trazer para frente

pasta = filedialog.askdirectory(
    title="Selecionar Pasta com XMLs",
    initialdir=str(Path.home() / "Desktop")
)

root.destroy()

if pasta:
    print(pasta)
'''
    
    try:
        # No executável (PyInstaller), sys.executable é o .exe e não suporta '-c'.
        # Chamamos o próprio executável em um modo especial que só abre o seletor.
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, '--pick-xml-folder']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,
            )
        else:
            # Executar o script em processo separado
            result = subprocess.run(
                [sys.executable, '-c', script],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos de timeout
            )
        
        pasta = (result.stdout or '').strip()
        if pasta:
            logger.info(f"Pasta de XMLs selecionada: {pasta}")
            return pasta
            
    except subprocess.TimeoutExpired:
        logger.warning("Timeout ao aguardar seleção de pasta")
    except Exception as e:
        logger.error(f"Erro ao selecionar pasta: {e}")
    
    return None


def obter_pasta_xmls_salva():
    """
    Obtém a pasta de XMLs salva nas preferências
    
    Returns:
        str: Caminho da pasta ou None se não estiver salva
    """
    garantir_diretorio_config()
    
    try:
        if PREFS_FILE.exists():
            with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                pasta = prefs.get('pasta_xmls')
                if pasta and Path(pasta).exists():
                    logger.info(f"Pasta de XMLs recuperada: {pasta}")
                    return pasta
    except Exception as e:
        logger.error(f"Erro ao ler preferências: {e}")
    
    return None


def salvar_pasta_xmls(pasta):
    """
    Salva a pasta de XMLs nas preferências
    
    Args:
        pasta: Caminho da pasta para salvar
    """
    garantir_diretorio_config()
    
    try:
        prefs = {}
        if PREFS_FILE.exists():
            with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
        
        prefs['pasta_xmls'] = str(pasta)
        
        with open(PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Pasta de XMLs salva: {pasta}")
    except Exception as e:
        logger.error(f"Erro ao salvar preferências: {e}")


def selecionar_ou_usar_pasta_xmls_salva():
    """Obtém a pasta de XMLs.

    Regras:
    - Se já existe uma pasta salva e ela existe no disco, usa automaticamente.
    - O usuário pode alterar a qualquer momento (opção explícita "Alterar").
    - Se não existe pasta salva, abre o seletor de pasta (primeira vez).

    Returns:
        str: Caminho da pasta ou None
    """
    pasta_salva = obter_pasta_xmls_salva()

    # Primeira vez (ou pasta inválida): pedir seleção
    if not pasta_salva:
        nova_pasta = selecionar_pasta_xmls()
        if nova_pasta:
            salvar_pasta_xmls(nova_pasta)
            return nova_pasta
        return None

    # Já existe pasta salva: usar automaticamente, mas permitir alterar
    root = tk.Tk()
    root.withdraw()

    alterar = messagebox.askyesno(
        "Pasta de XMLs",
        f"Pasta salva encontrada:\n\n{pasta_salva}\n\nDeseja ALTERAR a pasta?\n\n(Sim = alterar | Não = usar a salva)"
    )

    root.destroy()

    if not alterar:
        return pasta_salva

    nova_pasta = selecionar_pasta_xmls()
    if nova_pasta:
        salvar_pasta_xmls(nova_pasta)
        return nova_pasta

    # Se o usuário cancelou a troca, mantém a salva
    return pasta_salva


def confirmar_acao(titulo, mensagem):
    """
    Mostra diálogo de confirmação
    
    Args:
        titulo: Título do diálogo
        mensagem: Mensagem a exibir
        
    Returns:
        bool: True se usuário clicou OK, False caso contrário
    """
    root = tk.Tk()
    root.withdraw()
    
    resultado = messagebox.askyesno(titulo, mensagem)
    
    root.destroy()
    
    return resultado


def mostrar_mensagem(titulo, mensagem, tipo='info'):
    """
    Mostra mensagem ao usuário
    
    Args:
        titulo: Título da janela
        mensagem: Mensagem a exibir
        tipo: 'info', 'warning' ou 'error'
    """
    root = tk.Tk()
    root.withdraw()
    
    if tipo == 'error':
        messagebox.showerror(titulo, mensagem)
    elif tipo == 'warning':
        messagebox.showwarning(titulo, mensagem)
    else:
        messagebox.showinfo(titulo, mensagem)
    
    root.destroy()
