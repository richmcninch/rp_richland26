# Compile rp_richland26 using GMod's own Source compile tools (x86-64 build)
# Output BSP is copied to the srcds maps folder automatically.

$GmodBin  = "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64"
$GmodGame = "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod"
$Vmf      = "$PSScriptRoot\rp_richland26.vmf"
$MapBase  = "$PSScriptRoot\rp_richland26"   # no extension; tools resolve .vmf/.bsp themselves
$BspDest  = "F:\richbots\server\garrysmod\maps\rp_richland26.bsp"

# Parse flags
$FastVis  = $args -contains "-fast"
$NoCopy   = $args -contains "-nocopy"

$VbspOnly = $args -contains "-vbspOnly"
$VvisOnly = $args -contains "-vvisOnly"
$VradOnly = $args -contains "-vradOnly"

$RunVbsp = $true
$RunVvis = $true
$RunVrad = $true

if ($VbspOnly -or $VvisOnly -or $VradOnly) {
    $RunVbsp = $VbspOnly
    $RunVvis = $VvisOnly
    $RunVrad = $VradOnly
}

Write-Host "=== rp_richland26 compile ===" -ForegroundColor Cyan
Write-Host "VMF:  $Vmf"
Write-Host "Game: $GmodGame"
Write-Host ""

if (-not (Test-Path $Vmf)) {
    Write-Error "VMF not found: $Vmf"
    exit 1
}

# --- VBSP ---
if ($RunVbsp) {
    Write-Host "[1/3] vbsp" -ForegroundColor Yellow
    & "$GmodBin\vbsp.exe" -game "$GmodGame" "$MapBase"
    if ($LASTEXITCODE -ne 0) { Write-Error "vbsp failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
} else {
    Write-Host "[1/3] vbsp (skipped)" -ForegroundColor DarkYellow
}

# --- VVIS ---
if ($RunVvis) {
    Write-Host "[2/3] vvis" -ForegroundColor Yellow
    $VisArgs = @("-game", "$GmodGame")
    if ($FastVis) { $VisArgs += "-fast" }
    & "$GmodBin\vvis.exe" @VisArgs "$MapBase"
    if ($LASTEXITCODE -ne 0) { Write-Error "vvis failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
} else {
    Write-Host "[2/3] vvis (skipped)" -ForegroundColor DarkYellow
}

# --- VRAD ---
if ($RunVrad) {
    Write-Host "[3/3] vrad (HDR + LDR)" -ForegroundColor Yellow
    $RadArgs = @("-game", "$GmodGame", "-hdr", "-both", "-bounce", "100", "-final")
    & "$GmodBin\vrad.exe" @RadArgs "$MapBase"
    if ($LASTEXITCODE -ne 0) { Write-Error "vrad failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
} else {
    Write-Host "[3/3] vrad (skipped)" -ForegroundColor DarkYellow
}

# --- Copy BSP to srcds ---
$BspSrc = "$PSScriptRoot\rp_richland26.bsp"
if ($NoCopy) {
    Write-Host ""
    Write-Host "Copy step skipped (-nocopy)." -ForegroundColor DarkYellow
} elseif (Test-Path $BspSrc) {
    Write-Host ""
    Write-Host "Copying BSP -> $BspDest" -ForegroundColor Green
    Copy-Item -Force $BspSrc $BspDest

    # Also copy to local GMod client so client map matches server on connect.
    $ClientMapsDest = "$GmodGame\maps\rp_richland26.bsp"
    Write-Host "Copying BSP -> $ClientMapsDest" -ForegroundColor Green
    Copy-Item -Force $BspSrc $ClientMapsDest

    # Sync custom content to client garrysmod folder (suppress errors if GMod has files locked).
    foreach ($folder in @("materials", "models", "sound", "scripts")) {
        $src = Join-Path $PSScriptRoot $folder
        $dst = Join-Path $GmodGame $folder
        if (Test-Path $src) {
            Copy-Item -Recurse -Force "$src\*" "$dst\" -ErrorAction SilentlyContinue
        }
    }

    Write-Host "Done. Load with: changelevel rp_richland26" -ForegroundColor Green
} else {
    Write-Warning "BSP not found at expected location: $BspSrc"
}
