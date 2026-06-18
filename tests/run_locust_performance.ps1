param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("perf", "max-stress", "i5-stress", "table-realistic")]
    [string]$Scenario,

    [switch]$NoBuild,
    [switch]$NoSeed,

    # Useful for exploratory stress tests where Locust is expected to find the breaking point.
    [switch]$AllowFailure,

    # Runs `docker compose down -v` before and after the test.
    # Use only if the compose files use disposable volumes.
    [switch]$CleanVolumes,

    # Leaves the app container running after the test for inspection.
    [switch]$KeepApp,

    [ValidateRange(1, 60)]
    [int]$StatsIntervalSeconds = 2,

    [ValidateRange(10, 900)]
    [int]$ReadinessTimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw "Command failed with exit code ${exitCode}: ${FilePath} $($Arguments -join ' ')"
    }
}

function Invoke-Capture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    $output = & $FilePath @Arguments 2>&1
    $exitCode = $LASTEXITCODE

    return [pscustomobject]@{
        Output = $output
        ExitCode = $exitCode
    }
}

function Assert-DockerReady {
    $output = & docker info 2>&1
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Host $output
        throw "Docker is not ready. Start Docker Desktop, wait until it is running, and make sure Linux containers are enabled."
    }
}

function Get-GitCommit {
    try {
        $commit = (& git rev-parse HEAD 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and $commit) {
            return $commit
        }
    } catch {
        return $null
    }

    return $null
}

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir

$scenarioConfig = @{
    "perf" = @{
        ComposeFile = "docker-compose.perf.yml"
        OutputRoot = "performance"
        SeedFile = "performance/seed.py"
        Description = "20 users / spawn 2/s / 90s"
        Resources = "1 CPU / 4 GB"
        Role = "baseline"
    }

    "max-stress" = @{
        ComposeFile = "docker-compose.max-stress.yml"
        OutputRoot = "performance/max_stress"
        SeedFile = "performance/max_stress/seed.py"
        Description = "500 users / spawn 20/s / 300s"
        Resources = "1 CPU / 4 GB"
        Role = "breaking-point"
    }

    "i5-stress" = @{
        ComposeFile = "docker-compose.i5-stress.yml"
        OutputRoot = "performance/i5_stress"
        SeedFile = "performance/i5_stress/seed.py"
        Description = "500 users / spawn 20/s / 300s"
        Resources = "6 CPUs / 8 GB / 1 worker"
        Role = "vertical-headroom"
    }

    "table-realistic" = @{
        ComposeFile = "docker-compose.table-realistic.yml"
        OutputRoot = "performance/table_realistic"
        SeedFile = "performance/table_realistic/seed.py"
        Description = "15 users / 3 tables / realistic session"
        Resources = "1 CPU / 4 GB / 1 worker"
        Role = "product-acceptance"
    }
}

$config = $scenarioConfig[$Scenario]

$composeFile = Join-Path $scriptDir $config.ComposeFile
$outputRoot = Join-Path $rootDir $config.OutputRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = Join-Path $outputRoot $timestamp

# Seed paths are relative to tests/, not repo root.
$seedFile = Join-Path $scriptDir $config.SeedFile

$dbPath = Join-Path $rootDir "storage/gravewright.sqlite3"

$locustOutput = Join-Path $outputDir "locust.log"
$statsOutput = Join-Path $outputDir "docker_stats.tsv"
$metadataOutput = Join-Path $outputDir "metadata.json"

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

if (-not (Test-Path $composeFile)) {
    throw "Compose file not found: $composeFile"
}

if (-not $NoSeed -and -not (Test-Path $seedFile)) {
    throw "Seed file not found: $seedFile"
}

$metadata = [ordered]@{
    scenario = $Scenario
    role = $config.Role
    description = $config.Description
    resources = $config.Resources
    startedAt = (Get-Date).ToString("o")
    rootDir = $rootDir
    scriptDir = $scriptDir
    composeFile = $composeFile
    seedFile = if ($NoSeed) { $null } else { $seedFile }
    sqlitePath = $dbPath
    noBuild = [bool]$NoBuild
    noSeed = [bool]$NoSeed
    allowFailure = [bool]$AllowFailure
    cleanVolumes = [bool]$CleanVolumes
    keepApp = [bool]$KeepApp
    statsIntervalSeconds = $StatsIntervalSeconds
    readinessTimeoutSeconds = $ReadinessTimeoutSeconds
    gitCommit = Get-GitCommit
    powershellVersion = $PSVersionTable.PSVersion.ToString()
    os = [System.Environment]::OSVersion.VersionString
}

$metadata | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $metadataOutput

Write-Host "Scenario:    $Scenario"
Write-Host "Description: $($config.Description)"
Write-Host "Resources:   $($config.Resources)"
Write-Host "Compose:     $composeFile"
Write-Host "Output:      $outputDir"

$appStarted = $false
$statsJob = $null
$locustExit = 0

try {
    Write-Section "Checking Docker"
    Assert-DockerReady

    if ($CleanVolumes) {
        Write-Section "Cleaning compose stack and volumes"
        & docker compose -f $composeFile down -v --remove-orphans
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose down -v failed"
        }
    }

    if (-not $NoSeed) {
        Write-Section "Seeding database"
        Write-Host "DB:   $dbPath"
        Write-Host "Seed: $seedFile"
        Invoke-Checked python $seedFile --db $dbPath
    } else {
        Write-Section "Skipping seed"
    }

    if (-not $NoBuild) {
        Write-Section "Building containers"
        Invoke-Checked docker compose -f $composeFile build
    } else {
        Write-Section "Skipping build"
    }

    Write-Section "Starting app"
    Invoke-Checked docker compose -f $composeFile up -d app
    $appStarted = $true

    Write-Section "Waiting for app HTTP readiness"

    $appPortOutput = (& docker compose -f $composeFile port app 8000 2>$null).Trim()

    if ($appPortOutput) {
        $appPort = ($appPortOutput -split ":")[-1]
    } else {
        $appPort = "8000"
    }

    $healthUrl = "http://localhost:$appPort/"
    Write-Host "Readiness URL: $healthUrl"

    $ready = $false

    for ($i = 0; $i -lt $ReadinessTimeoutSeconds; $i++) {
        $psOutput = & docker compose -f $composeFile ps -a app 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            Write-Host $psOutput
            throw "docker compose ps failed while waiting for app readiness."
        }

        if ($psOutput -match "Exit|Exited") {
            Write-Host ""
            Write-Host "App container exited before becoming ready."
            Write-Host ""
            Write-Host "Compose state:"
            & docker compose -f $composeFile ps -a

            Write-Host ""
            Write-Host "Last app logs:"
            & docker compose -f $composeFile logs --tail=300 app

            throw "App container exited before becoming ready."
        }

        try {
            $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2

            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                $ready = $true
                Write-Host "App ready: $healthUrl -> HTTP $($response.StatusCode)"
                break
            }
        } catch {
            # Not ready yet.
        }

        if ($i % 5 -eq 0) {
            Write-Host "Still waiting for app HTTP readiness... ${i}s"
            & docker compose -f $composeFile ps -a app
        }

        Start-Sleep -Seconds 1
    }

    if (-not $ready) {
        Write-Host ""
        Write-Host "App did not become HTTP-ready. Current compose state:"
        & docker compose -f $composeFile ps -a

        Write-Host ""
        Write-Host "Last app logs:"
        & docker compose -f $composeFile logs --tail=300 app

        throw "App did not become HTTP-ready within $ReadinessTimeoutSeconds seconds."
    }

    $appContainer = (& docker compose -f $composeFile ps -q app).Trim()

    if (-not $appContainer) {
        Write-Host ""
        Write-Host "Compose state:"
        & docker compose -f $composeFile ps -a
        throw "Could not resolve app container ID after readiness."
    }

    Write-Section "Starting docker stats capture"

    $statsJob = Start-Job -ArgumentList $appContainer, $statsOutput, $StatsIntervalSeconds -ScriptBlock {
        param($Container, $OutputFile, $IntervalSeconds)

        "timestamp`tname`tcpu`tmem_usage`tmem_perc`tnet_io`tblock_io" | Set-Content -Encoding UTF8 $OutputFile

        while ($true) {
            $ts = Get-Date -Format o
            $line = docker stats --no-stream --format "{{.Name}}`t{{.CPUPerc}}`t{{.MemUsage}}`t{{.MemPerc}}`t{{.NetIO}}`t{{.BlockIO}}" $Container 2>&1

            if ($LASTEXITCODE -eq 0) {
                "$ts`t$line" | Add-Content -Encoding UTF8 $OutputFile
            } else {
                "$ts`tDOCKER_STATS_ERROR`t$line" | Add-Content -Encoding UTF8 $OutputFile
            }

            Start-Sleep -Seconds $IntervalSeconds
        }
    }

    Write-Section "Running Locust"

    # Capture the Docker/Locust exit code before Tee-Object so PowerShell pipeline behavior
    # does not hide the real process result.
    $result = Invoke-Capture docker compose -f $composeFile run --rm locust
    $locustExit = $result.ExitCode
    $result.Output | Tee-Object -FilePath $locustOutput

    if ($locustExit -ne 0) {
        Write-Warning "Locust finished with exit code $locustExit."
        if (-not $AllowFailure) {
            throw "Locust failed. Re-run with -AllowFailure for exploratory breaking-point stress tests."
        }
    }

    Write-Section "Done"
    Write-Host "Results: $outputDir"
    Write-Host "Locust:  $locustOutput"
    Write-Host "Stats:   $statsOutput"
    Write-Host "Meta:    $metadataOutput"
}
finally {
    if ($statsJob) {
        Stop-Job $statsJob -ErrorAction SilentlyContinue
        Receive-Job $statsJob -ErrorAction SilentlyContinue | Out-Null
        Remove-Job $statsJob -Force -ErrorAction SilentlyContinue
    }

    if ($appStarted -and -not $KeepApp) {
        Write-Section "Stopping compose stack"
        if ($CleanVolumes) {
            & docker compose -f $composeFile down -v --remove-orphans
        } else {
            & docker compose -f $composeFile down --remove-orphans
        }
    } elseif ($KeepApp) {
        Write-Warning "Keeping app container running because -KeepApp was set."
    }
}

if ($locustExit -ne 0 -and -not $AllowFailure) {
    exit $locustExit
}

exit 0
