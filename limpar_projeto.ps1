Param(
  [switch]$IncludeDeps,
  [switch]$IncludeRuntimeData
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootResolved = (Resolve-Path $Root).Path
$excludedPrefixes = @(
  (Join-Path $rootResolved '.venv'),
  (Join-Path $rootResolved 'frontend\node_modules')
)

function Test-InsideWorkspace([string]$targetPath) {
  $resolved = [System.IO.Path]::GetFullPath($targetPath)
  return $resolved.StartsWith($rootResolved, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-IsExcluded([string]$targetPath) {
  $resolved = [System.IO.Path]::GetFullPath($targetPath)

  foreach ($prefix in $excludedPrefixes) {
    if ($resolved.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }

  return $false
}

function Remove-ProjectPath([string]$relativePath) {
  $target = Join-Path $rootResolved $relativePath
  if (-not (Test-Path -LiteralPath $target)) {
    return
  }

  if (-not (Test-InsideWorkspace $target)) {
    throw "Caminho fora do workspace: $target"
  }

  Write-Host "[REMOVENDO] $relativePath"
  Remove-Item -LiteralPath $target -Recurse -Force
}

$targets = @(
  'build',
  'dist',
  'UltraDanfeXML_Portable',
  'output',
  'logs',
  'frontend\dist',
  'static\dist',
  'build_log.txt'
)

if ($IncludeDeps) {
  $targets += @(
    '.venv',
    'frontend\node_modules'
  )
}

if ($IncludeRuntimeData) {
  $targets += @(
    'config\historico_boletos',
    'config\historico_put.json',
    'config\preferencias.json'
  )
}

foreach ($target in $targets) {
  Remove-ProjectPath $target
}

$pycacheDirs = Get-ChildItem -LiteralPath $rootResolved -Recurse -Directory -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -eq '__pycache__' -and -not (Test-IsExcluded $_.FullName) }

foreach ($dir in $pycacheDirs) {
  if (-not (Test-InsideWorkspace $dir.FullName)) {
    throw "Diretorio fora do workspace: $($dir.FullName)"
  }

  $display = $dir.FullName.Substring($rootResolved.Length).TrimStart('\')
  Write-Host "[REMOVENDO] $display"
  Remove-Item -LiteralPath $dir.FullName -Recurse -Force
}

$pycFiles = Get-ChildItem -LiteralPath $rootResolved -Recurse -File -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.Extension -in '.pyc', '.pyo' -and -not (Test-IsExcluded $_.FullName) }

foreach ($file in $pycFiles) {
  if (-not (Test-InsideWorkspace $file.FullName)) {
    throw "Arquivo fora do workspace: $($file.FullName)"
  }

  $display = $file.FullName.Substring($rootResolved.Length).TrimStart('\')
  Write-Host "[REMOVENDO] $display"
  Remove-Item -LiteralPath $file.FullName -Force
}

Write-Host ""
Write-Host "Limpeza concluida."
