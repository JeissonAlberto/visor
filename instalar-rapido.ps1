$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/JeissonAlberto/visor.git'
$root = Join-Path $HOME 'visor-v52'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git no está instalado o no está disponible en PATH.'
}
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python 3.10 o superior no está instalado o no está disponible en PATH.'
}

if (Test-Path (Join-Path $root '.git')) {
    git -C $root pull --ff-only origin main
} elseif (Test-Path $root) {
    throw "La carpeta $root existe pero no es un clon Git válido. Respáldala o elige otra ruta."
} else {
    git clone $repo $root
}

Push-Location $root
try {
    $env:VISOR_NO_PAUSE = '1'
    & cmd.exe /c '.\instalar.bat'
    if ($LASTEXITCODE -ne 0) { throw 'La instalación de Visor no terminó correctamente.' }
} finally {
    Remove-Item Env:VISOR_NO_PAUSE -ErrorAction SilentlyContinue
    Pop-Location
}

Write-Host ''
Write-Host 'Listo. Cierra esta ventana, abre una nueva PowerShell y escribe: visor' -ForegroundColor Green
