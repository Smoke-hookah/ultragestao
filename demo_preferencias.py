#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de demonstração da Interface Gráfica
Mostra como usar a GUI sem necessidade de arquivo Excel real
"""

from pathlib import Path
import sys

# Adiciona o diretório do projeto ao PATH
sys.path.insert(0, str(Path(__file__).parent))

from utils.ui import (
    obter_pasta_xmls_salva,
    salvar_pasta_xmls,
    mostrar_mensagem
)
from utils.logger import logger
import json


def demo_preferencias():
    """Demonstra o sistema de preferências"""
    
    print("\n" + "="*70)
    print("🎨 DEMONSTRAÇÃO - Sistema de Preferências")
    print("="*70 + "\n")
    
    # 1. Verificar se há preferência salva
    pasta_salva = obter_pasta_xmls_salva()
    
    if pasta_salva:
        print(f"✅ Pasta de XMLs salva encontrada:")
        print(f"   📁 {pasta_salva}\n")
    else:
        print("❌ Nenhuma pasta de XMLs salva ainda\n")
    
    # 2. Salvar nova preferência (simulado com Desktop)
    print("💾 Salvando preferência de exemplo...")
    pasta_exemplo = str(Path.home() / "Desktop")
    salvar_pasta_xmls(pasta_exemplo)
    print(f"   ✓ Salvo: {pasta_exemplo}\n")
    
    # 3. Recuperar e validar
    pasta_recuperada = obter_pasta_xmls_salva()
    print(f"🔍 Verificando se foi salvo corretamente...")
    print(f"   ✓ Recuperado: {pasta_recuperada}\n")
    
    # 4. Mostrar arquivo JSON
    prefs_file = Path(__file__).parent / "config" / "preferencias.json"
    print(f"📄 Conteúdo do arquivo de preferências:")
    print(f"   📍 {prefs_file}")
    
    if prefs_file.exists():
        with open(prefs_file, 'r', encoding='utf-8') as f:
            conteudo = json.load(f)
        
        print(f"   Conteúdo JSON:")
        for chave, valor in conteudo.items():
            print(f"     {chave}: {valor}")
    
    print("\n" + "="*70)
    print("✅ Demonstração Concluída!")
    print("="*70)
    print("\nPróximos passos:")
    print("1. Execute: python main.py --gui")
    print("2. Selecione sua planilha Excel")
    print("3. Selecione uma pasta com XMLs")
    print("4. Na próxima execução, pode reutilizar a pasta!")
    print("="*70 + "\n")


if __name__ == "__main__":
    demo_preferencias()
