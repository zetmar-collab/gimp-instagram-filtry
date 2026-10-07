# Instaluje filtry Instagram i „Obramowanie tekstu” do GIMP 3.x (Windows).
# Użycie:  powershell -ExecutionPolicy Bypass -File .\install.ps1 [-Version 3.2]
param(
    [string]$Version
)

$ErrorActionPreference = "Stop"
$gimpRoot = Join-Path $env:APPDATA "GIMP"

if (-not $Version) {
    # Najnowszy katalog konfiguracji 3.x (np. 3.0, 3.2), bez kopii zapasowych.
    $dir = Get-ChildItem $gimpRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^3\.\d+$' } |
        Sort-Object { [version]$_.Name } -Descending |
        Select-Object -First 1
    if (-not $dir) {
        throw "Nie znaleziono katalogu $gimpRoot\3.x - uruchom GIMP 3 raz albo podaj -Version."
    }
    $Version = $dir.Name
}

$dest = Join-Path $gimpRoot "$Version\plug-ins"
New-Item -ItemType Directory -Force $dest | Out-Null
foreach ($name in "instagram-filtry", "text-border") {
    $target = Join-Path $dest $name
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
    Copy-Item (Join-Path $PSScriptRoot $name) $dest -Recurse
    Write-Host "Zainstalowano: $target"
}
Write-Host "Uruchom ponownie GIMP. Menu: Filtry -> Instagram oraz Warstwa -> Tekst -> Dodaj obramowanie tekstu."
