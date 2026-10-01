<#
.SYNOPSIS
    Publica develop a master y dispara el deploy de ARGOS a producción.

.DESCRIPTION
    Corre la puerta de calidad local (verify.sh), hace el merge fast-forward
    de develop a master, empuja el cambio, espera que CI del commit en master
    termine en verde y dispara el workflow de GitHub Actions "Deploy ARGOS to
    Production" con confirmar=PRODUCCION. Ese workflow ejecuta el patrón de
    candidato + batería de humo + rollback por SSH desde el runner de GitHub
    Actions; no hace falta ejecutar nada a mano en la VPS.

.PARAMETER Confirmar
    Requerido. Confirma que se quiere desplegar a producción.

.PARAMETER Watch
    Monitorea el workflow de deploy hasta que termine.

.PARAMETER CiTimeoutMinutos
    Minutos máximos de espera por CI verde en master. Por defecto 30.

.EXAMPLE
    .\deploy-produccion.ps1 -Confirmar

.EXAMPLE
    .\deploy-produccion.ps1 -Confirmar -Watch
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = 'Confirma el despliegue a producción')]
    [switch]$Confirmar,

    [Parameter(HelpMessage = 'Monitorea el workflow de deploy hasta que termine')]
    [switch]$Watch,

    [Parameter(HelpMessage = 'Minutos máximos de espera por CI verde en master')]
    [int]$CiTimeoutMinutos = 30,

    [string]$RamaDesarrollo = 'develop',
    [string]$RamaProduccion = 'master',
    [string]$Workflow = 'deploy-argos.yml'
)

$ErrorActionPreference = 'Stop'

function Test-Programa {
    param([string]$Nombre)
    $null -ne (Get-Command $Nombre -ErrorAction SilentlyContinue)
}

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Argumentos)
    $salida = & git @Argumentos 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $Argumentos falló: $salida"
    }
    return $salida
}

function Get-RefSha {
    param([string]$Ref)
    return Invoke-Git 'rev-parse' $Ref
}

function Wait-CiVerde {
    param(
        [string]$Sha,
        [int]$TimeoutMinutos
    )

    $limite = [DateTime]::UtcNow.AddMinutes($TimeoutMinutos)
    Write-Host "Esperando CI verde para $Sha (timeout ${TimeoutMinutos}m)..."

    while ([DateTime]::UtcNow -lt $limite) {
        $run = gh run list --workflow=ci.yml --branch=$RamaProduccion --limit=1 --json conclusion,headSha,status,displayTitle,url | ConvertFrom-Json
        if ($run -and $run[0].headSha -eq $Sha) {
            $estado = $run[0].status
            $conclusion = $run[0].conclusion
            Write-Host "  CI estado=$estado conclusion=$conclusion"
            if ($estado -eq 'completed') {
                if ($conclusion -eq 'success') {
                    return $run[0]
                }
                throw "CI del commit $Sha no fue exitoso (conclusion=$conclusion). URL: $($run[0].url)"
            }
        }
        else {
            Write-Host '  Aún no aparece el run de CI para este commit...'
        }
        Start-Sleep -Seconds 15
    }

    throw "Timeout esperando CI verde para $Sha"
}

# ---------------------------------------------------------------------------
# Validaciones iniciales
# ---------------------------------------------------------------------------

if (-not $Confirmar) {
    throw 'El despliegue a producción requiere -Confirmar. Ejemplo: .\deploy-produccion.ps1 -Confirmar'
}

if (-not (Test-Programa 'git')) {
    throw 'git no está disponible en PATH'
}

if (-not (Test-Programa 'gh')) {
    throw 'GitHub CLI (gh) no está disponible en PATH'
}

if (-not (Test-Programa 'bash')) {
    throw 'bash no está disponible en PATH (necesario para verify.sh)'
}

gh auth status >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    throw 'GitHub CLI (gh) no está autenticado. Ejecuta gh auth login.'
}

$raiz = Invoke-Git 'rev-parse' '--show-toplevel'
Set-Location $raiz

# ---------------------------------------------------------------------------
# Puerta de calidad local
# ---------------------------------------------------------------------------

Write-Host 'Ejecutando puerta de calidad local...'
& bash './verify.sh'
if ($LASTEXITCODE -ne 0) {
    throw 'La puerta de calidad local falló. Corrige antes de publicar.'
}
Write-Host 'Puerta de calidad local verde.' -ForegroundColor Green

$ramaActual = Invoke-Git 'branch' '--show-current'
if ($ramaActual -ne $RamaDesarrollo) {
    throw "Debes estar en la rama '$RamaDesarrollo' para publicar. Rama actual: $ramaActual"
}

$estado = Invoke-Git 'status' '--short'
if (-not [string]::IsNullOrWhiteSpace($estado)) {
    throw "El working tree tiene cambios sin commitear. Resuélvelos antes de publicar.`n$estado"
}

# ---------------------------------------------------------------------------
# Publicar develop -> master (fast-forward)
# ---------------------------------------------------------------------------

Write-Host "Publicando $RamaDesarrollo -> $RamaProduccion..."

Invoke-Git 'fetch' 'origin'

$shaDevelopLocal = Get-RefSha $RamaDesarrollo
$shaDevelopRemoto = Get-RefSha "origin/$RamaDesarrollo"
if ($shaDevelopLocal -ne $shaDevelopRemoto) {
    throw "La rama local '$RamaDesarrollo' ($shaDevelopLocal) no coincide con 'origin/$RamaDesarrollo' ($shaDevelopRemoto). Haz push primero."
}

$shaMasterLocal = Get-RefSha $RamaProduccion
$shaMasterRemoto = Get-RefSha "origin/$RamaProduccion"
if ($shaMasterLocal -ne $shaMasterRemoto) {
    throw "La rama local '$RamaProduccion' ($shaMasterLocal) no coincide con 'origin/$RamaProduccion' ($shaMasterRemoto). Revisa manualmente."
}

if ($shaMasterLocal -eq $shaDevelopLocal) {
    Write-Host "$RamaProduccion ya está alineado con $RamaDesarrollo ($shaDevelopLocal). No hay merge que hacer." -ForegroundColor Green
}
else {
    Invoke-Git 'checkout' $RamaProduccion
    try {
        Invoke-Git 'pull' 'origin' $RamaProduccion
        Invoke-Git 'merge' '--ff-only' $RamaDesarrollo
        Invoke-Git 'push' 'origin' $RamaProduccion
    }
    catch {
        Write-Host "Fallo durante merge/push a $RamaProduccion. Volviendo a $RamaDesarrollo..." -ForegroundColor Red
        Invoke-Git 'checkout' $RamaDesarrollo
        throw
    }
    Invoke-Git 'checkout' $RamaDesarrollo
}

$shaRelease = Get-RefSha "origin/$RamaProduccion"
Write-Host "Commit a desplegar: $shaRelease" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Esperar CI verde en master
# ---------------------------------------------------------------------------

$runCi = Wait-CiVerde -Sha $shaRelease -TimeoutMinutos $CiTimeoutMinutos
Write-Host "CI verde: $($runCi.url)" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Disparar deploy a producción
# ---------------------------------------------------------------------------

Write-Host "Disparando workflow $Workflow con confirmar=PRODUCCION..."
$salidaDeploy = gh workflow run $Workflow --ref $RamaProduccion -f confirmar=PRODUCCION 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo disparar el workflow deploy: $salidaDeploy"
}
Write-Host $salidaDeploy -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Monitorear (opcional)
# ---------------------------------------------------------------------------

if ($Watch) {
    Start-Sleep -Seconds 5
    $run = gh run list --workflow=$Workflow --branch=$RamaProduccion --limit=1 --json databaseId,headSha,status | ConvertFrom-Json
    if ($run -and $run[0].headSha -eq $shaRelease) {
        $runId = $run[0].databaseId
        Write-Host "Monitoreando deploy (run $runId)..."
        gh run watch $runId --exit-status
        if ($LASTEXITCODE -ne 0) {
            $repo = $env:GITHUB_REPOSITORY
            if (-not $repo) {
                $repo = gh repo view --json nameWithOwner -q '.nameWithOwner'
            }
            throw "El deploy falló. Revisa https://github.com/$repo/actions/runs/$runId"
        }
        Write-Host 'Deploy completado exitosamente.' -ForegroundColor Green
    }
    else {
        Write-Warning 'No se encontró el run de deploy recién disparado para monitorear.'
    }
}
else {
    Write-Host 'Deploy disparado. Usa -Watch para monitorearlo o revisa la pestaña Actions en GitHub.' -ForegroundColor Green
}
