import os
import ftplib
import subprocess
import sys
from pathlib import Path

# --- CONFIGURAÇÕES DO HOST ---
FTP_HOST = "ftp.homebake.com.br"
FTP_USER = "appSPHostgator@appsp.homebake.com.br"
FTP_PASS = "APPsp1912$#@!"
REMOTE_DIR = "/ultadanfe"

# Arquivos e pastas do backend para subir
BACKEND_FILES = [
    "api.py",
    "config.py",
    "requirements.txt",
    "passenger_wsgi.py",
    ".env",
    ".htaccess",
]
BACKEND_DIRS = [
    "models",
    "services",
    "utils",
]

# Pasta do build do frontend (conforme configurado no vite.config)
FRONTEND_DIST = Path("static/dist")

def run_command(cmd, cwd=None):
    print(f"Executando: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Erro ao executar comando: {cmd}")
        sys.exit(1)

def upload_directory(ftp, local_path, remote_path):
    print(f"Subindo diretório: {local_path} -> {remote_path}")
    try:
        ftp.mkd(remote_path)
    except:
        pass # Pasta já existe

    for item in os.listdir(local_path):
        l_item = os.path.join(local_path, item)
        r_item = f"{remote_path}/{item}"
        
        if os.path.isfile(l_item):
            with open(l_item, "rb") as f:
                print(f"  Subindo arquivo: {item}")
                ftp.storbinary(f"STOR {r_item}", f)
                try:
                    ftp.voidcmd(f"SITE CHMOD 755 {r_item}")
                except:
                    pass
        elif os.path.isdir(l_item) and item not in [".git", "node_modules", "__pycache__"]:
            upload_directory(ftp, l_item, r_item)
            try:
                ftp.voidcmd(f"SITE CHMOD 755 {r_item}")
            except:
                pass

def deploy():
    # 1. Build do Frontend
    print("--- 1. Fazendo build do Frontend ---")
    if not os.path.exists("frontend"):
        print("Pasta frontend não encontrada!")
        return
    
    run_command("npm install", cwd="frontend")
    run_command("npm run build", cwd="frontend")

    # 2. Conectar ao FTP
    print(f"--- 2. Conectando ao FTP: {FTP_HOST} ---")
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    
    try:
        # Criar pasta base se não existir
        try:
            ftp.mkd(REMOTE_DIR)
        except:
            pass
        
        # 3. Subir arquivos do Backend
        print("--- 3. Subindo arquivos do Backend ---")
        for f_name in BACKEND_FILES:
            if os.path.exists(f_name):
                with open(f_name, "rb") as f:
                    print(f"  Subindo: {f_name}")
                    ftp.storbinary(f"STOR {REMOTE_DIR}/{f_name}", f)
                    try:
                        ftp.voidcmd(f"SITE CHMOD 755 {REMOTE_DIR}/{f_name}")
                    except:
                        pass
        
        for d_name in BACKEND_DIRS:
            if os.path.exists(d_name):
                upload_directory(ftp, d_name, f"{REMOTE_DIR}/{d_name}")

        # 4. Subir arquivos do Frontend (estáticos)
        print("--- 4. Subindo Frontend (static/dist) ---")
        # No nosso api.py, o STATIC_FOLDER aponta para static/dist
        remote_static = f"{REMOTE_DIR}/static"
        remote_dist = f"{remote_static}/dist"
        
        try:
            ftp.mkd(remote_static)
        except:
            pass
            
        upload_directory(ftp, str(FRONTEND_DIST), remote_dist)

        print("\n[OK] DEPLOY CONCLUIDO COM SUCESSO!")
        print(f"Acesse: http://homebake.com.br{REMOTE_DIR}")
        print("Nota: Certifique-se de configurar o Python App no painel da Hostinger apontando para passenger_wsgi.py")

    finally:
        ftp.quit()

def get_logs():
    print(f"--- Baixando logs de: {FTP_HOST} ---")
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    try:
        remote_log = f"{REMOTE_DIR}/error_log.txt"
        local_log = "remote_error_log.txt"
        with open(local_log, "wb") as f:
            ftp.retrbinary(f"RETR {remote_log}", f.write)
        print(f"[OK] Log baixado com sucesso: {local_log}")
        with open(local_log, "r", encoding="utf-8", errors="replace") as f:
            print("\n--- CONTEÚDO DO LOG ---")
            print(f.read())
    except Exception as e:
        print(f"X Erro ao baixar log (talvez o arquivo ainda nao exista): {e}")
    finally:
        ftp.quit()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "logs":
        get_logs()
    else:
        deploy()
