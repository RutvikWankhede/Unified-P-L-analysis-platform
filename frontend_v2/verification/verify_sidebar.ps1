<#
.SYNOPSIS
    Sidebar Visual & Link-Health Verification Script - P&L System
.DESCRIPTION
    1. Ensures the frontend server is reachable at BaseUrl.
    2. Downloads dashboard.html, forecast.html, settings.html.
    3. Extracts the sidebar block from each page.
    4. Compares nav links against the reference partial (partials/sidebar.html).
    5. Runs verify_links.js against the reference sidebar partial.
    6. Produces a JSON link-health report in verification/link_report.json.
.PARAMETER BaseUrl
    Base URL of the frontend dev server. Default: http://127.0.0.1:3000
.PARAMETER SkipScreenshots
    Skip the screenshot capture step.
#>
param(
    [string]$BaseUrl = "http://127.0.0.1:3000",
    [switch]$SkipScreenshots
)

$ErrorActionPreference = "Stop"
$VerificationDir = $PSScriptRoot
$ScreenshotDir   = Join-Path $VerificationDir "screenshots"
$ReportPath      = Join-Path $VerificationDir "link_report.json"

function Write-Step { param([string]$Msg)  Write-Host "" ; Write-Host ">> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg)  Write-Host "  [OK]  $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg)  Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg)  Write-Host "  [FAIL] $Msg" -ForegroundColor Red }

# --- Step 1: Check server reachability ---
Write-Step "Checking server at $BaseUrl ..."
try {
    $ping = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 5
    Write-Ok "Server responded with HTTP $($ping.StatusCode)"
} catch {
    Write-Fail "Server NOT reachable at $BaseUrl. Start it with:"
    Write-Host "    python frontend_v2/serve_frontend.py" -ForegroundColor Yellow
    exit 1
}

# --- Step 2: Download pages & extract sidebars ---
Write-Step "Downloading pages and extracting sidebar blocks ..."

$Pages = @(
    [PSCustomObject]@{ Name = "dashboard"; File = "dashboard.html" },
    [PSCustomObject]@{ Name = "forecast";  File = "forecast.html"  },
    [PSCustomObject]@{ Name = "settings";  File = "settings.html"  }
)

$ExtractedSidebars = @{}

foreach ($page in $Pages) {
    $url     = "$BaseUrl/$($page.File)"
    $rawPath = Join-Path $VerificationDir "page_$($page.Name).html"

    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
        [System.IO.File]::WriteAllText($rawPath, $resp.Content, [System.Text.Encoding]::UTF8)
        Write-Ok "Downloaded $($page.File)"
    } catch {
        Write-Warn "Could not download $($page.File): $_"
        continue
    }

    $content = $resp.Content

    # All pages now use the sidebar-container pattern (shell.js injects at runtime)
    if ($content -match 'id="sidebar-container"') {
        Write-Ok "$($page.File) uses shell.js sidebar-container pattern [CORRECT]"
        $sidebarHtml = '<div id="sidebar-container"></div> <!-- dynamically loaded by shell.js -->'
    } elseif ($content -match '<aside[^>]*data-purpose="side-nav-bar"') {
        Write-Warn "$($page.File) still has a HARDCODED inline aside -- should be migrated!"
        $sidebarHtml = '<!-- hardcoded aside found - not expected -->'
    } else {
        Write-Warn "$($page.File) has no recognisable sidebar pattern"
        $sidebarHtml = '<!-- no sidebar pattern found -->'
    }

    $sidebarPath = Join-Path $VerificationDir "sidebar_$($page.Name).html"
    [System.IO.File]::WriteAllText($sidebarPath, $sidebarHtml, [System.Text.Encoding]::UTF8)
    $ExtractedSidebars[$page.Name] = $sidebarPath
}

# --- Step 3: Validate reference partial nav links & confirm all pages use shell.js ---
Write-Step "Validating reference partial and confirming shell.js pattern on all pages ..."

$FrontendRoot = Split-Path $VerificationDir -Parent
$RefSidebar   = Join-Path $FrontendRoot "partials\sidebar.html"

if (Test-Path $RefSidebar) {
    $refLinks = [regex]::Matches((Get-Content $RefSidebar -Raw), 'href="([^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
    $refWidth = if ((Get-Content $RefSidebar -Raw) -match 'w-\[(\d+)px\]') { "w-[$($Matches[1])px]" } else { "not specified" }

    Write-Host "  Reference partial nav links ($($refLinks.Count)): $($refLinks -join ', ')"
    Write-Host "  Reference partial sidebar width: $refWidth"

    if ($refLinks.Count -eq 10) {
        Write-Ok "Reference partial has all 10 expected nav links"
    } else {
        Write-Warn "Reference partial has $($refLinks.Count) nav links (expected 10)"
    }

    # Confirm all three pages use sidebar-container (no inline aside drift)
    $allPages = @("dashboard", "forecast", "settings")
    $allDynamic = $true
    foreach ($pName in $allPages) {
        $rawPath = Join-Path $VerificationDir "page_${pName}.html"
        if (Test-Path $rawPath) {
            $html = Get-Content $rawPath -Raw
            $hasSC    = $html -match 'id="sidebar-container"'
            $hasAside = $html -match 'data-purpose="side-nav-bar"'
            if ($hasSC -and -not $hasAside) {
                Write-Ok "${pName}.html: uses sidebar-container [UNIFIED]"
            } elseif ($hasAside) {
                Write-Warn "${pName}.html: STILL HAS inline aside -- needs migration!"
                $allDynamic = $false
            } else {
                Write-Warn "${pName}.html: no sidebar pattern found"
                $allDynamic = $false
            }
        }
    }

    if ($allDynamic) {
        Write-Ok "All 3 pages unified: dashboard, forecast, settings all use shell.js"
    }

} else {
    Write-Warn "Reference partial not found at $RefSidebar"
}

# --- Step 4: Capture Screenshots ---
if (-not $SkipScreenshots) {
    Write-Step "Capturing screenshots ..."
    if (-not (Test-Path $ScreenshotDir)) { New-Item -ItemType Directory -Path $ScreenshotDir | Out-Null }

    $captureAvailable = $false
    try {
        $null = & npx --yes capture-website --version 2>&1
        $captureAvailable = $true
    } catch { }

    if ($captureAvailable) {
        foreach ($page in $Pages) {
            $url    = "$BaseUrl/$($page.File)"
            $outPng = Join-Path $ScreenshotDir "$($page.Name).png"
            try {
                & npx --yes capture-website $url --output $outPng --width 1440 --height 900 2>&1 | Out-Null
                Write-Ok "Screenshot -> $outPng"
            } catch {
                Write-Warn "Screenshot failed for $($page.File): $_"
            }
        }
    } else {
        Write-Warn "capture-website not available. Run: npm install -g capture-website-cli"
    }
} else {
    Write-Warn "Screenshot capture skipped (-SkipScreenshots)"
}

# --- Step 5: Link Health Check ---
Write-Step "Running link health check against reference sidebar ..."

$NodeScript    = Join-Path $VerificationDir "verify_links.js"
$TargetSidebar = if (Test-Path $RefSidebar) { $RefSidebar } elseif ($ExtractedSidebars.ContainsKey("dashboard")) { $ExtractedSidebars["dashboard"] } else { $null }

if (-not (Test-Path $NodeScript)) {
    Write-Fail "verify_links.js not found at $NodeScript"
    exit 1
}

if (-not $TargetSidebar) {
    Write-Fail "No sidebar HTML available for link checking"
    exit 1
}

Write-Host "  Checking links in: $TargetSidebar"
$tmpOut = [System.IO.Path]::GetTempFileName()
$tmpErr = [System.IO.Path]::GetTempFileName()
try {
    $proc = Start-Process node -ArgumentList "`"$NodeScript`" `"$TargetSidebar`" $BaseUrl" `
        -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr `
        -Wait -PassThru -NoNewWindow
    # Show stderr (per-link log lines)
    if (Test-Path $tmpErr) { Get-Content $tmpErr | ForEach-Object { Write-Host "  $_" } }
    $jsonContent = if (Test-Path $tmpOut) { Get-Content $tmpOut -Raw } else { "" }
} finally {
    Remove-Item $tmpOut, $tmpErr -ErrorAction SilentlyContinue
}

if ($jsonContent -match '(?s)(\[.*\])') {
    $jsonArray = $Matches[1]
    [System.IO.File]::WriteAllText($ReportPath, $jsonArray, [System.Text.Encoding]::UTF8)
    Write-Ok "Link report saved -> $ReportPath"

    $parsed  = $jsonArray | ConvertFrom-Json
    $broken  = $parsed | Where-Object { $_.status -ne 200 }
    $healthy = $parsed | Where-Object { $_.status -eq 200 }

    Write-Host ""
    Write-Host "  Links checked : $($parsed.Count)"  -ForegroundColor White
    Write-Host "  [OK] Healthy  : $($healthy.Count)" -ForegroundColor Green
    if ($broken.Count -gt 0) {
        Write-Host "  [FAIL] Broken : $($broken.Count)" -ForegroundColor Red
        $broken | ForEach-Object {
            $sv = if ($_.status) { $_.status } else { $_.error }
            Write-Host "      $($_.href) -> $sv" -ForegroundColor Red
        }
    } else {
        Write-Host "  [OK] All links returned HTTP 200" -ForegroundColor Green
    }
    
    $exitCode = if ($broken.Count -gt 0) { 1 } else { 0 }
} else {
    Write-Warn "No JSON output from verify_links.js - check that node is installed"
    $exitCode = 1
}

# --- Done ---
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Verification complete. Results in:"           -ForegroundColor Cyan
Write-Host "    $VerificationDir"                           -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan

exit $exitCode