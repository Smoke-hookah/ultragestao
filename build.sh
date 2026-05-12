#!/usr/bin/env bash
# Sair em caso de erro
set -o errexit

# Instalar dependências do Python
pip install -r requirements.txt

# Instalar navegadores do Playwright e dependências do sistema
playwright install --with-deps chromium
