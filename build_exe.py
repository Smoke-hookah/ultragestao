#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de build automatizado para gerar o executavel.
Usa apenas caracteres ASCII para compatibilidade com terminal Windows.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
STATIC_DIST_DIR = BASE_DIR / "static" / "dist"
LEGACY_FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
SPEC_FILE = BASE_DIR / "UltraDanfeXML.spec"
PLAYWRIGHT_BROWSERS_DIR = BASE_DIR / "playwright-browsers"

def print_step(msg):
    """Imprime mensagem de etapa."""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")

def run_command(cmd, cwd=None, shell=True, env=None):
    """Executa comando e retorna sucesso."""
    try:
        print(f"> {cmd}")
        result = subprocess.run(
            cmd,
            shell=shell,
            check=True,
            cwd=cwd or BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
            encoding='cp850',
            errors='replace'
        )
        if result.stdout:
            # Limita output para não lotar console
            lines = result.stdout.strip().split('\n')
            if len(lines) > 20:
                print('\n'.join(lines[:10]))
                print(f"... ({len(lines)-20} linhas omitidas) ...")
                print('\n'.join(lines[-10:]))
            else:
                print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falhou: {cmd}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        print(f"[ERRO] Excecao: {e}")
        return False

def has_playwright_runtime(path: Path) -> bool:
    """Verifica se existe um Chromium do Playwright pronto para empacotar."""
    if not path.exists():
        return False
    return any(path.rglob("chrome.exe")) or any(path.rglob("headless_shell.exe"))


def find_bundled_playwright_runtime(package_dir: Path) -> Path | None:
    """Localiza o runtime dentro do pacote final."""
    candidates = [
        package_dir / "playwright-browsers",
        package_dir / "_internal" / "playwright-browsers",
    ]
    for candidate in candidates:
        if has_playwright_runtime(candidate):
            return candidate
    return None

def ensure_playwright_runtime():
    """Garante que o runtime do Chromium do Playwright esteja disponivel localmente."""
    print_step("3/5 - Preparando browser embutido do Protheus")

    if has_playwright_runtime(PLAYWRIGHT_BROWSERS_DIR):
        print(f"[OK] Runtime Playwright encontrado em: {PLAYWRIGHT_BROWSERS_DIR}")
        return True

    print("[INFO] Runtime Playwright nao encontrado. Tentando baixar Chromium...")
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_DIR)

    cmd = f'"{sys.executable}" -m playwright install chromium'
    if not run_command(cmd, env=env):
        print("[ERRO] Nao foi possivel baixar o Chromium do Playwright.")
        print("[DICA] Instale a dependencia e rode novamente:")
        print(f'       "{sys.executable}" -m pip install playwright')
        print(f'       "{sys.executable}" -m playwright install chromium')
        return False

    if not has_playwright_runtime(PLAYWRIGHT_BROWSERS_DIR):
        print("[ERRO] O download terminou, mas o runtime do Chromium nao foi encontrado.")
        return False

    print(f"[OK] Runtime Playwright preparado em: {PLAYWRIGHT_BROWSERS_DIR}")
    return True

def clean_build():
    """Remove diretorios de build anteriores."""
    print_step("1/4 - Limpando builds anteriores")
    
    for dir_path in [DIST_DIR, BUILD_DIR, STATIC_DIST_DIR, LEGACY_FRONTEND_DIST_DIR]:
        if dir_path.exists():
            print(f"Removendo: {dir_path}")
            shutil.rmtree(dir_path)
    
    print("[OK] Limpeza concluida")
    return True

def build_frontend():
    """Compila o frontend React."""
    print_step("2/4 - Compilando frontend React")
    
    if not FRONTEND_DIR.exists():
        print("[ERRO] Diretorio frontend nao encontrado!")
        return False
    
    # npm run build
    print("Compilando frontend com Vite...")
    if not run_command("npm run build", cwd=FRONTEND_DIR):
        return False
    
    if not STATIC_DIST_DIR.exists():
        print("[ERRO] Build do frontend nao foi gerado em static/dist!")
        return False
    
    print(f"[OK] Frontend compilado em: {STATIC_DIST_DIR}")
    return True

def build_executable():
    """Gera o executavel com PyInstaller."""
    print_step("4/5 - Gerando executavel com PyInstaller")
    
    if not SPEC_FILE.exists():
        print("[ERRO] Arquivo UltraDanfeXML.spec nao encontrado!")
        return False
    
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        print("[AVISO] Arquivo .env encontrado no projeto.")
        print("        Ele NAO sera embutido no executavel por seguranca.")
        print("        Use um .env externo ao lado do .exe quando precisar de API_KEY/API_KEYS.")
    else:
        print("[INFO] Nenhum .env local encontrado.")
        print("       O executavel sera gerado para usar .env externo ou modo local.")
    
    print("Executando PyInstaller...")
    cmd = f'"{sys.executable}" -m PyInstaller --noconfirm --clean "{SPEC_FILE.name}"'
    if not run_command(cmd):
        print("[DICA] Instale PyInstaller no mesmo ambiente usado para este script:")
        print(f'       "{sys.executable}" -m pip install pyinstaller')
        return False
    
    app_dir = DIST_DIR / "UltraDanfeXML"
    exe_file = app_dir / "UltraDanfeXML.exe"
    internal_dir = app_dir / "_internal"

    if not app_dir.exists():
        print("[ERRO] Pasta da aplicacao nao foi gerada!")
        return False
    if not exe_file.exists():
        print("[ERRO] Executavel nao foi gerado!")
        return False
    if not internal_dir.exists():
        print("[ERRO] Pasta _internal nao foi gerada!")
        return False
    
    print(f"[OK] Aplicacao standalone gerada em: {app_dir}")
    print(f"     Executavel: {exe_file}")
    print(f"     Tamanho do EXE: {exe_file.stat().st_size / (1024*1024):.2f} MB")
    return True

def remove_dir_with_retry(path, max_retries=3):
    """Remove diretorio com retry para arquivos em uso."""
    import time
    
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"Tentativa {attempt + 1}/{max_retries}: Aguardando arquivos serem liberados...")
                time.sleep(1)
            else:
                # Ultima tentativa: tentar remover apenas arquivos especificos
                print(f"Removendo apenas o executavel antigo...")
                exe_old = path / "UltraDanfeXML.exe"
                readme_old = path / "LEIA-ME.txt"
                try:
                    if exe_old.exists():
                        exe_old.unlink()
                    if readme_old.exists():
                        readme_old.unlink()
                except:
                    pass
                return True
    return False

def create_package():
    """Cria pacote portavel com a pasta standalone."""
    print_step("5/5 - Criando pacote portavel")
    
    package_dir = BASE_DIR / "UltraDanfeXML_Portable"
    app_dir = DIST_DIR / "UltraDanfeXML"
    exe_source = app_dir / "UltraDanfeXML.exe"

    if not app_dir.exists() or not exe_source.exists():
        print("[ERRO] Aplicacao standalone nao encontrada!")
        return False

    if package_dir.exists():
        print(f"Removendo pacote anterior: {package_dir}")
        if not remove_dir_with_retry(package_dir):
            print("[ERRO] Nao foi possivel remover o pacote anterior.")
            return False

    print("Copiando aplicacao standalone...")
    shutil.copytree(app_dir, package_dir)

    bundled_browser_dir = find_bundled_playwright_runtime(package_dir)
    if bundled_browser_dir is None:
        print("[ERRO] O pacote final nao contem o runtime do Chromium do Playwright.")
        return False

    env_example_src = BASE_DIR / ".env.example"
    if env_example_src.exists():
        shutil.copy2(env_example_src, package_dir / ".env.example")
    
    # Criar LEIA-ME.txt
    readme = package_dir / "LEIA-ME.txt"
    readme.write_text("""=================================================================
  ULTRADANFE XML - VERSAO EXECUTAVEL
=================================================================

COMO USAR:

1. Execute UltraDanfeXML.exe
2. O navegador abrira automaticamente
3. Configure a pasta de XMLs e comece a processar!

REQUISITOS:

- Windows 10 ou superior
- Conexao com internet apenas quando usar a API Meu Danfe

 OBSERVACOES:

- Nao e necessario instalar Python ou Node.js
- O aplicativo e standalone (auto-contido)
- Mantenha o .exe e a pasta _internal juntos
- Coloque um arquivo .env ao lado do .exe se quiser usar API_KEY/API_KEYS
- Existe um arquivo .env.example para servir de modelo
- Arquivos processados: pasta 'output'
- Logs: pasta 'logs'
- Preferencias e historicos: pasta 'config'

EM CASO DE PROBLEMAS:

- Verifique sua conexao com internet
- Verifique se o antivirus nao esta bloqueando
- Execute via terminal para ver mensagens de erro
- Se for usar somente DANFE local, o sistema pode iniciar sem API_KEY

SUPORTE:

Para mais informacoes, consulte a documentacao completa no projeto.

Versao: 1.0
Data: Janeiro 2026
=================================================================
""", encoding='utf-8')
    
    exe_dest = package_dir / "UltraDanfeXML.exe"
    print(f"[OK] Pacote criado em: {package_dir}")
    print(f"     Executavel: {exe_dest.name}")
    print(f"     Tamanho do EXE: {exe_dest.stat().st_size / (1024*1024):.2f} MB")
    return True

def main():
    """Funcao principal."""
    print("\n" + "="*60)
    print("  BUILD ULTRADANFE XML - EXECUTAVEL STANDALONE")
    print("="*60)
    
    try:
        # Etapa 1
        if not clean_build():
            print("\n[ERRO] Falha na limpeza")
            sys.exit(1)
        
        # Etapa 2
        if not build_frontend():
            print("\n[ERRO] Falha no build do frontend")
            sys.exit(1)

        # Etapa 3
        if not ensure_playwright_runtime():
            print("\n[ERRO] Falha ao preparar o browser embutido")
            sys.exit(1)

        # Etapa 4
        if not build_executable():
            print("\n[ERRO] Falha ao gerar executavel")
            sys.exit(1)

        # Etapa 5
        if not create_package():
            print("\n[ERRO] Falha ao criar pacote")
            sys.exit(1)
        
        # Sucesso
        print("\n" + "="*60)
        print("  [OK] BUILD CONCLUIDO COM SUCESSO!")
        print("="*60)
        print(f"\nExecutavel disponivel em:")
        print(f"  {BASE_DIR / 'UltraDanfeXML_Portable' / 'UltraDanfeXML.exe'}")
        print("\nDistribua a pasta 'UltraDanfeXML_Portable' completa.")
        print("\nPROXIMOS PASSOS:")
        print("1. Abra a pasta UltraDanfeXML_Portable")
        print("2. Execute UltraDanfeXML.exe")
        print("3. Nao separe a pasta _internal do executavel")
        print("4. Se precisar da API Meu Danfe, crie um .env ao lado do .exe")
        print("5. Aguarde o navegador abrir automaticamente")
        print("6. Comece a processar seus XMLs!")
        print("\nOBS: O build nao embute .env nem historicos locais no executavel.")
        
    except KeyboardInterrupt:
        print("\n\n[ERRO] Build cancelado pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERRO] Erro durante build: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
