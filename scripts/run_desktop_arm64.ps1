tparam(
    [Parameter(Mandatory = $true)]
    [ValidateSet('check', 'build', 'dev')]
    [string]$Mode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$desktopDir = Join-Path $repoRoot 'desktop'

if (-not (Test-Path $desktopDir)) {
    throw "desktop directory not found: $desktopDir"
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) {
    throw "vswhere not found: $vswhere"
}

$vsPath = (& $vswhere -latest -products * -version '[18.0,19.0)' -property installationPath | Select-Object -First 1).Trim()
if ([string]::IsNullOrWhiteSpace($vsPath)) {
    throw 'Visual Studio 18.x installation not found via vswhere.'
}

$vsDevCmd = Join-Path $vsPath 'Common7\Tools\VsDevCmd.bat'
if (-not (Test-Path $vsDevCmd)) {
    throw "VsDevCmd.bat not found: $vsDevCmd"
}

function Get-ToolchainGuardBlock {
    @(
        'where cl >nul 2>nul',
        'if errorlevel 1 (echo [ERROR] cl not found after VsDevCmd & exit /b 1)',
        'where link >nul 2>nul',
        'if errorlevel 1 (echo [ERROR] link not found after VsDevCmd & exit /b 1)',
        'where clang >nul 2>nul',
        'if errorlevel 1 (echo [ERROR] clang not found after VsDevCmd & exit /b 1)',
        'if "%VCINSTALLDIR%"=="" (echo [ERROR] VCINSTALLDIR is unset & exit /b 1)',
        'if "%WindowsSdkDir%"=="" (echo [ERROR] WindowsSdkDir is unset & exit /b 1)',
        'if "%INCLUDE%"=="" (echo [ERROR] INCLUDE is unset & exit /b 1)',
        'if "%LIB%"=="" (echo [ERROR] LIB is unset & exit /b 1)'
    ) -join [Environment]::NewLine
}

function Invoke-InVs18DevShell {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandBody
    )

    $tmpCmd = [System.IO.Path]::GetTempFileName() + '.cmd'
    try {
        $cmdScript = @(
            '@echo off',
            ('call "{0}" -arch=arm64 -host_arch=arm64 -no_logo' -f $vsDevCmd),
            'if errorlevel 1 exit /b %errorlevel%',
            $CommandBody,
            'exit /b %errorlevel%'
        ) -join [Environment]::NewLine

        Set-Content -Path $tmpCmd -Value $cmdScript -Encoding Ascii
        & cmd.exe /d /c """$tmpCmd"""
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed in VS18 dev shell (exit $LASTEXITCODE)."
        }
    }
    finally {
        Remove-Item -Path $tmpCmd -ErrorAction SilentlyContinue
    }
}

Write-Host "[INFO] Repo root: $repoRoot"
Write-Host "[INFO] VS18 path: $vsPath"
Write-Host "[INFO] VsDevCmd: $vsDevCmd"
Write-Host "[INFO] Mode: $Mode"

switch ($Mode) {
    'check' {
        $checkAndReport = @(
            (Get-ToolchainGuardBlock),
            'where cl',
            'where link',
            'where clang',
            'echo VCINSTALLDIR=%VCINSTALLDIR%',
            'echo WindowsSdkDir=%WindowsSdkDir%',
            'echo INCLUDE_SET=1',
            'echo LIB_SET=1',
            'echo [PASS] VS18 ARM64 developer environment validated'
        ) -join [Environment]::NewLine
        Invoke-InVs18DevShell -CommandBody $checkAndReport
    }
    'build' {
        $buildCmd = @(
            (Get-ToolchainGuardBlock),
            ('cd /d "{0}"' -f $desktopDir),
            'npm run build'
        ) -join [Environment]::NewLine
        Invoke-InVs18DevShell -CommandBody $buildCmd
    }
    'dev' {
        $devCmd = @(
            (Get-ToolchainGuardBlock),
            ('cd /d "{0}"' -f $desktopDir),
            'npm run dev'
        ) -join [Environment]::NewLine
        Invoke-InVs18DevShell -CommandBody $devCmd
    }
    default {
        throw "Unsupported mode: $Mode"
    }
}
