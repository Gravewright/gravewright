param(
    [switch]$NoBuild,
    [switch]$NoSeed,
    [switch]$AllowFailure,
    [switch]$CleanVolumes,
    [switch]$KeepApp
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "run_locust_performance.ps1") `
    -Scenario i5-stress `
    -NoBuild:$NoBuild `
    -NoSeed:$NoSeed `
    -AllowFailure:$AllowFailure `
    -CleanVolumes:$CleanVolumes `
    -KeepApp:$KeepApp

exit $LASTEXITCODE
