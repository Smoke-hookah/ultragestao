Param(
  [switch]$Gui,
  [switch]$Api,
  [switch]$Frontend,
  [switch]$Full,
  [switch]$SkipInstall,
  [int]$Port = 5000
)

$ErrorActionPreference = 'Stop'

function Write-Info([string]$msg) { Write-Host "[INFO] $msg" }
function Write-Warn([string]$msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg) { Write-Host "[ERRO] $msg" -ForegroundColor Red }

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$EnvFile = Join-Path $Root '.env'
$EnvExample = Join-Path $Root '.env.example'
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Requirements = Join-Path $Root 'requirements.txt'
$FrontendDir = Join-Path $Root 'frontend'

function Ensure-Env {
  if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
      Copy-Item $EnvExample $EnvFile
      Write-Warn "Arquivo .env não existia; copiei de .env.example. Configure a API_KEY antes de usar."
    } else {
      Write-Warn "Arquivo .env não encontrado e .env.example também não. Você precisa criar .env manualmente."
    }
  }
}

function Ensure-Venv {
  $needsRecreate = $false
  if (Test-Path $VenvPython) {
    # Venv pode existir mas estar quebrada (apontando para um Python removido em outro caminho/usuário)
    try {
      & $VenvPython -c "import sys; print(sys.executable)" | Out-Null
    } catch {
      $needsRecreate = $true
      Write-Warn "A .venv existe, mas está inválida (Python base não encontrado). Vou recriar." 
    }

    if (-not $needsRecreate) { return }
  }

  if ($needsRecreate -and (Test-Path (Join-Path $Root '.venv'))) {
    Remove-Item -Recurse -Force (Join-Path $Root '.venv')
  }

  Write-Info "Criando ambiente virtual em .venv..."

  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    py -3 -m venv .venv
  } else {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
      throw "Python não encontrado no PATH. Instale Python 3.10+ e tente novamente."
    }
    python -m venv .venv
  }

  if (-not (Test-Path $VenvPython)) {
    throw "Falha ao criar .venv (python.exe não encontrado)."
  }
}

function Install-BackendDeps {
  if (-not (Test-Path $Requirements)) {
    Write-Warn "requirements.txt não encontrado; pulando instalação do backend."
    return
  }

  Write-Info "Instalando dependências Python (requirements.txt)..."
  & $VenvPython -m pip install --upgrade pip
  & $VenvPython -m pip install -r $Requirements
}

function Install-FrontendDeps {
  if (-not (Test-Path $FrontendDir)) {
    Write-Warn "Pasta frontend não encontrada; pulando instalação do frontend."
    return
  }

  $npm = Get-Command npm -ErrorAction SilentlyContinue
  if (-not $npm) {
    throw "npm não encontrado no PATH. Instale Node.js LTS (inclui npm) para rodar o frontend."
  }

  Write-Info "Instalando dependências do frontend (npm install)..."
  Push-Location $FrontendDir
  try {
    npm install
  } finally {
    Pop-Location
  }
}

function Start-Gui {
  Write-Info "Iniciando GUI..."
  & $VenvPython (Join-Path $Root 'main.py') --gui
}

function Start-Api {
  Write-Info "Iniciando API em http://localhost:$Port ..."
  # O main.py fixa porta 5000 atualmente; manter coerência.
  & $VenvPython (Join-Path $Root 'main.py') --api
}

function Start-Frontend {
  Write-Info "Iniciando frontend (Vite) em modo dev..."
  Push-Location $FrontendDir
  try {
    npm run dev
  } finally {
    Pop-Location
  }
}

function Show-Menu {
  Write-Host ""
  Write-Host "UltraDanfeXML - Inicializar" -ForegroundColor Cyan
  Write-Host "1) Abrir GUI (selecionar planilha/pasta XML)"
  Write-Host "2) Iniciar apenas API (backend)"
  Write-Host "3) Iniciar API + Frontend (2 janelas)"
  Write-Host "4) Sair"
  Write-Host ""
  $choice = Read-Host "Escolha uma opção (1-4)"
  switch ($choice) {
    '1' { $script:Gui = $true }
    '2' { $script:Api = $true }
    '3' { $script:Full = $true }
    default { return $false }
  }
  return $true
}

Ensure-Env

if (-not ($Gui -or $Api -or $Frontend -or $Full)) {
  $ok = Show-Menu
  if (-not $ok) { exit 0 }
}

$needBackend = ($Gui -or $Api -or $Full)
$needFrontend = ($Frontend -or $Full)

if (-not $SkipInstall) {
  if ($needBackend) {
    Ensure-Venv
    Install-BackendDeps
  }
  if ($needFrontend) {
    Install-FrontendDeps
  }
} else {
  if ($needBackend -and -not (Test-Path $VenvPython)) {
    Write-Warn "-SkipInstall foi usado, mas .venv não existe; a execução pode falhar."
  }
}

if ($Full) {
  # Iniciar API e Frontend em janelas separadas
  if (-not (Test-Path $VenvPython)) { Ensure-Venv }

  $apiCmd = "cd `"$Root`"; `"$VenvPython`" `"$Root\main.py`" --api"
  $feCmd = "cd `"$FrontendDir`"; npm run dev"

  Write-Info "Abrindo 2 janelas (API + Frontend)..."
  Start-Process -FilePath powershell -ArgumentList "-NoExit", "-Command", $apiCmd | Out-Null
  Start-Process -FilePath powershell -ArgumentList "-NoExit", "-Command", $feCmd | Out-Null
  exit 0
}

if ($Gui) { Start-Gui; exit 0 }
if ($Api) { Start-Api; exit 0 }
if ($Frontend) { Start-Frontend; exit 0 }

Write-Err "Nenhuma opção selecionada."
exit 1
