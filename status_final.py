#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script final de status da interface gráfica"""

import json
from pathlib import Path

print('\n' + '='*80)
print('INTERFACE GRAFICA - IMPLEMENTACAO COMPLETA'.center(80))
print('='*80 + '\n')

prefs_file = Path('config/preferencias.json')
if prefs_file.exists():
    with open(prefs_file, 'r') as f:
        prefs = json.load(f)
    print('✓ Sistema de Preferencias:')
    print(f'  Arquivo: config/preferencias.json')
    print(f'  Pasta Salva: {prefs.get("pasta_xmls", "Nenhuma")}')
else:
    print('○ Sistema de Preferencias: (criado na primeira execucao)')

print()
print('='*80)
print('NOVOS ARQUIVOS (5):')
print('='*80)

arquivos = [
    ('utils/ui.py', 'Interface grafica com tkinter'),
    ('services/leitor_xml.py', 'Leitor de XMLs da pasta'),
    ('interface_grafica.py', 'Aplicacao principal'),
    ('demo_preferencias.py', 'Script de teste'),
    ('config/ (diretorio)', 'Armazena preferencias.json'),
]

for i, (arquivo, descricao) in enumerate(arquivos, 1):
    print(f'  {i}. {arquivo:<30} → {descricao}')

print()
print('='*80)
print('DOCUMENTACAO CRIADA (5):')
print('='*80)

docs = [
    'GUI_QUICK_START.md',
    'README_GUI.md',
    'SUMARIO_EXECUTIVO.md',
    'GUI_GUIDE.md',
    'INDICE_ARQUIVOS.md',
]

for i, doc in enumerate(docs, 1):
    print(f'  {i}. {doc}')

print()
print('='*80)
print('COMO USAR:')
print('='*80)
print('  1. Abra Terminal')
print('  2. Digite: python main.py --gui')
print('  3. Siga os passos na tela')

print()
print('='*80)
print('RECURSOS IMPLEMENTADOS:')
print('='*80)

recursos = [
    'Seletor visual de planilha Excel',
    'Seletor visual de pasta XMLs',
    'Sistema de cache/preferencias',
    'Oferta de reutilizar pasta',
    'Validacao de XMLs',
    'Fluxo guiado passo a passo',
    'Integracao com Orquestrador',
    'Suporte a 3 formas de execucao',
]

for i, recurso in enumerate(recursos, 1):
    print(f'  {i}. ✓ {recurso}')

print()
print('='*80)
print('STATUS FINAL: PRONTO PARA USAR!'.center(80))
print('='*80 + '\n')
