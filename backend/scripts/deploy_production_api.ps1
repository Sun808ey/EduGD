# Build a credential-free runtime bundle and upload it to the exact production API.
# Run under the Windows account authenticated with Railway CLI.
param([switch]$PrepareOnly)

$ErrorActionPreference = 'Stop'
$eduguardBackend = Split-Path -Parent $PSScriptRoot
$eduguardBundle = Join-Path ([IO.Path]::GetTempPath()) 'EduGuard-production-deploy-bundle'
$eduguardProject = '7d0c485e-3e9f-411c-9412-af8dd6f32481'
$eduguardEnvironment = '48e80896-15ef-4616-837e-d59240fc503a'
$eduguardService = '8e9b3d47-6efe-4e32-aef3-74fa69b99ef5'
$eduguardCa = Join-Path $eduguardBackend 'certs\supabase-ca.pem'

if (-not (Test-Path -LiteralPath $eduguardCa -PathType Leaf)) {
    throw 'Reviewed public Supabase CA is missing.'
}
$eduguardCertificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($eduguardCa)
try {
    if (-not $eduguardCertificate.Subject -or -not $eduguardCertificate.Issuer) {
        throw 'Reviewed public Supabase CA is invalid.'
    }
} finally {
    $eduguardCertificate.Dispose()
}

if (-not $PrepareOnly) {
    & railway whoami | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Railway CLI authentication is unavailable in this PowerShell.' }
}

$eduguardBundleRoot = [IO.Path]::GetFullPath($eduguardBundle)
$eduguardExpectedRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
if (-not $eduguardBundleRoot.StartsWith($eduguardExpectedRoot, [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $eduguardBundleRoot) -ne 'EduGuard-production-deploy-bundle') {
    throw 'Deployment bundle resolved outside the dedicated temporary path.'
}
if (Test-Path -LiteralPath $eduguardBundleRoot) {
    Remove-Item -LiteralPath $eduguardBundleRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $eduguardBundleRoot | Out-Null

foreach ($eduguardFile in ('requirements.txt', 'pyproject.toml', '.python-version', 'run.py', 'gunicorn.conf.py', 'railway.json', 'railpack.json')) {
    Copy-Item -LiteralPath (Join-Path $eduguardBackend $eduguardFile) -Destination $eduguardBundleRoot
}
$eduguardRailpackBytes = [IO.File]::ReadAllBytes((Join-Path $eduguardBundleRoot 'railpack.json'))
if ($eduguardRailpackBytes.Length -ge 3 -and
    $eduguardRailpackBytes[0] -eq 0xEF -and
    $eduguardRailpackBytes[1] -eq 0xBB -and
    $eduguardRailpackBytes[2] -eq 0xBF) {
    throw 'railpack.json must be UTF-8 without a byte-order mark.'
}
foreach ($eduguardDirectory in ('app', 'migrations')) {
    Copy-Item -LiteralPath (Join-Path $eduguardBackend $eduguardDirectory) -Destination $eduguardBundleRoot -Recurse
}
Get-ChildItem -LiteralPath $eduguardBundleRoot -Directory -Recurse -Force |
    Where-Object Name -eq '__pycache__' |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $eduguardBundleRoot -File -Recurse -Force |
    Where-Object Extension -in ('.pyc', '.pyo') |
    Remove-Item -Force
New-Item -ItemType Directory -Path (Join-Path $eduguardBundleRoot 'certs') | Out-Null
Copy-Item -LiteralPath $eduguardCa -Destination (Join-Path $eduguardBundleRoot 'certs\supabase-ca.pem')
New-Item -ItemType Directory -Path (Join-Path $eduguardBundleRoot 'scripts') | Out-Null
Copy-Item -LiteralPath (Join-Path $eduguardBackend 'scripts\verify_hosted_environment.py') -Destination (Join-Path $eduguardBundleRoot 'scripts\verify_hosted_environment.py')

# Inspect relative paths only; the temporary parent path is irrelevant.
$eduguardForbidden = Get-ChildItem -LiteralPath $eduguardBundleRoot -Recurse -Force -File |
    Where-Object {
        $eduguardRelative = $_.FullName.Substring($eduguardBundleRoot.TrimEnd('\').Length).TrimStart('\')
        $eduguardRelative -match '(?i)(^|[\\/])(\.env[^\\/]*|.*\.clixml|.*\.key|.*\.pfx|.*\.p12|id_rsa|id_ed25519)$'
    }
if ($eduguardForbidden) { throw 'Credential-like file detected in deployment bundle.' }

if ($PrepareOnly) {
    $eduguardFileCount = @(Get-ChildItem -LiteralPath $eduguardBundleRoot -Recurse -Force -File).Count
    Write-Output "PREPARED: sanitized production bundle with $eduguardFileCount files. No upload performed."
    return
}

Push-Location $eduguardBundleRoot
try {
    & railway up --detach --json `
        --project $eduguardProject `
        --environment $eduguardEnvironment `
        --service $eduguardService `
        --message 'Production API release after verified schema and runtime security'
    if ($LASTEXITCODE -ne 0) { throw 'Railway production upload failed.' }
} finally {
    Pop-Location
}
