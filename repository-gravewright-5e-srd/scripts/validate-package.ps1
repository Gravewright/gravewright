param(
  [Parameter(Mandatory = $true)]
  [string]$GravewrightRoot
)

$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $PSScriptRoot
$Target = Join-Path $GravewrightRoot "data\packages\rulesets\dnd5e"

New-Item -ItemType Directory -Force (Split-Path -Parent $Target) | Out-Null
if (Test-Path $Target) {
  Remove-Item -Recurse -Force $Target
}
Copy-Item -Recurse -Force $PackageRoot $Target

Push-Location $GravewrightRoot
try {
  uv run python -m app.cli package validate data/packages/rulesets/dnd5e
  uv run python -m app.cli package install dnd5e --enable
  uv run python -m app.cli package update dnd5e --json
  uv run python -m app.cli doctor --strict --json
}
finally {
  Pop-Location
}
