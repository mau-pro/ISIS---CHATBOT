# iniciar_beta.ps1
# ------------------
# Pone I-SIS en linea para la prueba BETA desde esta PC:
#   1. enciende Docker Desktop (si esta cerrado) y el sistema
#   2. crea un enlace publico temporal https://....trycloudflare.com (Cloudflare Quick Tunnel)
#   3. ajusta los enlaces de los correos (registro y recuperar contrasena) a ese enlace
#   4. muestra la direccion para repartir; al presionar Enter se apaga el enlace
#
# Uso: doble clic en "iniciar_beta.bat"  (o: powershell -ExecutionPolicy Bypass -File scripts\iniciar_beta.ps1)
# La PC debe quedar ENCENDIDA y CONECTADA mientras dure la beta.

param([switch]$Probar)   # -Probar: solo verifica y apaga el enlace al final, sin esperar Enter

$ErrorActionPreference = "Continue"  # docker escribe avisos normales por stderr: no deben cortar el script
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$env:Path = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;" + $env:Path
$cloudflared = @("${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:ProgramFiles\cloudflared\cloudflared.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $cloudflared) { Write-Host "Falta cloudflared. Instalalo con: winget install --id Cloudflare.cloudflared" -ForegroundColor Red; exit 1 }

$script:terminado = $false
function Terminar {
    if ($script:terminado) { return }
    $script:terminado = $true
    if ($tunel) { $tunel | Stop-Process -Force -ErrorAction SilentlyContinue }
    # Los correos vuelven a apuntar a esta PC (el enlace temporal ya no existe)
    $l = Get-Content $envFile | Where-Object { $_ -notmatch '^PUBLIC_URL=' }
    Set-Content -Path $envFile -Value ($l + "PUBLIC_URL=http://localhost") -Encoding ascii
    cmd /c "docker compose up -d >nul 2>&1"
    Write-Host "Enlace apagado. I-SIS sigue funcionando solo en esta PC (http://localhost)."
}

function Paso($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }

$envFile = Join-Path $raiz ".env"
$tunel = $null
try {

Paso "1/4 Docker"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Start-Process "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe"
    Write-Host "Abriendo Docker Desktop (puede tardar 1 o 2 minutos)..."
    for ($i = 0; $i -lt 60; $i++) { Start-Sleep 5; docker info *> $null; if ($LASTEXITCODE -eq 0) { break } }
    if ($LASTEXITCODE -ne 0) { Write-Host "Docker no arranco. Abrilo a mano y volve a ejecutar." -ForegroundColor Red; return }
}
Write-Host "Docker listo."

Paso "2/4 Enlace publico (Cloudflare)"
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
$log = Join-Path $env:TEMP "isis_tunel.log"
Remove-Item $log -ErrorAction SilentlyContinue
$tunel = Start-Process $cloudflared -ArgumentList "tunnel --no-autoupdate --url http://localhost:80" `
    -RedirectStandardError $log -WindowStyle Hidden -PassThru
$url = $null
for ($i = 0; $i -lt 45 -and -not $url; $i++) {
    Start-Sleep 2
    if (Test-Path $log) { $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value } }
}
if (-not $url) { Write-Host "No se obtuvo el enlace. Revisa tu conexion a internet." -ForegroundColor Red; return }
Write-Host "Enlace: $url"

Paso "3/4 Encender I-SIS con ese enlace (para los correos de registro)"
$lineas = Get-Content $envFile | Where-Object { $_ -notmatch '^PUBLIC_URL=' }
Set-Content -Path $envFile -Value ($lineas + "PUBLIC_URL=$url") -Encoding ascii
cmd /c "docker compose up -d >nul 2>&1"
$sano = $false
for ($i = 0; $i -lt 60; $i++) {
    if ((docker inspect -f "{{.State.Health.Status}}" asistente-universitario-backend-1 2>$null) -eq "healthy") { $sano = $true; break }
    Start-Sleep 4
}
if (-not $sano) { Write-Host "El backend no quedo listo. Mira: docker compose logs backend" -ForegroundColor Red }

Paso "4/4 Comprobacion desde internet"
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    try { if ((Invoke-WebRequest "$url/api/" -UseBasicParsing -TimeoutSec 15).StatusCode -eq 200) { $ok = $true; break } } catch { Start-Sleep 3 }
}
if ($ok) { Write-Host "I-SIS responde desde internet." -ForegroundColor Green } else { Write-Host "El enlace todavia no responde; espera un minuto y proba en el navegador." -ForegroundColor Yellow }

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host " DIRECCION PARA LOS ESTUDIANTES:" -ForegroundColor Green
Write-Host "   $url" -ForegroundColor White
Write-Host " Esta direccion CAMBIA cada vez que se inicia: compartila de nuevo." -ForegroundColor Yellow
Write-Host " Cuentas para repartir: backend\cuentas_beta.txt" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Set-Clipboard -Value $url -ErrorAction SilentlyContinue
Write-Host "(La direccion ya quedo copiada: pegala en WhatsApp o en un generador de QR.)"


if ($Probar) { Write-Host "Prueba terminada."; return }
Read-Host "`nNO CIERRES esta ventana. Presiona Enter para TERMINAR la beta y apagar el enlace"
Terminar

} finally {
    # Pase lo que pase (Enter, error o ventana cerrada con Ctrl+C) se apaga el enlace y se restaura la configuracion
    Terminar
}
