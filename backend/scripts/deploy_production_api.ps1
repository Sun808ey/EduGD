# Build a credential-free runtime bundle and upload it to the exact production API.
# Run under the Windows account authenticated with Railway CLI.
param([switch]$PrepareOnly)

$ErrorActionPreference = 'Stop'
$edugBackend = Split-Path -Parent $PSScriptRoot
$edugBundle = Join-Path ([IO.Path]::GetTempPath()) 'EduG-production-deploy-bundle'
$edugProject = '7d0c485e-3e9f-411c-9412-af8dd6f32481'
$edugEnvironment = '48e80896-15ef-4616-837e-d59240fc503a'
$edugService = '8e9b3d47-6efe-4e32-aef3-74fa69b99ef5'
$edugCa = Join-Path $edugBackend 'certs\supabase-ca.pem'

if (-not (Test-Path -LiteralPath $edugCa -PathType Leaf)) {
    throw 'Reviewed public Supabase CA is missing.'
}
$edugCertificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($edugCa)
try {
    if (-not $edugCertificate.Subject -or -not $edugCertificate.Issuer) {
        throw 'Reviewed public Supabase CA is invalid.'
    }
} finally {
    $edugCertificate.Dispose()
}

if (-not $PrepareOnly) {
    & railway whoami | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Railway CLI authentication is unavailable in this PowerShell.' }
}

$edugBundleRoot = [IO.Path]::GetFullPath($edugBundle)
$edugExpectedRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
if (-not $edugBundleRoot.StartsWith($edugExpectedRoot, [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $edugBundleRoot) -ne 'EduG-production-deploy-bundle') {
    throw 'Deployment bundle resolved outside the dedicated temporary path.'
}
if (Test-Path -LiteralPath $edugBundleRoot) {
    Remove-Item -LiteralPath $edugBundleRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $edugBundleRoot | Out-Null

foreach ($edugFile in ('requirements.txt', 'pyproject.toml', '.python-version', 'run.py', 'gunicorn.conf.py', 'railway.json', 'railpack.json')) {
    Copy-Item -LiteralPath (Join-Path $edugBackend $edugFile) -Destination $edugBundleRoot
}
$edugRailpackBytes = [IO.File]::ReadAllBytes((Join-Path $edugBundleRoot 'railpack.json'))
if ($edugRailpackBytes.Length -ge 3 -and
    $edugRailpackBytes[0] -eq 0xEF -and
    $edugRailpackBytes[1] -eq 0xBB -and
    $edugRailpackBytes[2] -eq 0xBF) {
    throw 'railpack.json must be UTF-8 without a byte-order mark.'
}
foreach ($edugDirectory in ('app', 'migrations')) {
    Copy-Item -LiteralPath (Join-Path $edugBackend $edugDirectory) -Destination $edugBundleRoot -Recurse
}
Get-ChildItem -LiteralPath $edugBundleRoot -Directory -Recurse -Force |
    Where-Object Name -eq '__pycache__' |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $edugBundleRoot -File -Recurse -Force |
    Where-Object Extension -in ('.pyc', '.pyo') |
    Remove-Item -Force
New-Item -ItemType Directory -Path (Join-Path $edugBundleRoot 'certs') | Out-Null
Copy-Item -LiteralPath $edugCa -Destination (Join-Path $edugBundleRoot 'certs\supabase-ca.pem')
New-Item -ItemType Directory -Path (Join-Path $edugBundleRoot 'scripts') | Out-Null
Copy-Item -LiteralPath (Join-Path $edugBackend 'scripts\verify_hosted_environment.py') -Destination (Join-Path $edugBundleRoot 'scripts\verify_hosted_environment.py')

# Inspect relative paths only; the temporary parent path is irrelevant.
$edugForbidden = Get-ChildItem -LiteralPath $edugBundleRoot -Recurse -Force -File |
    Where-Object {
        $edugRelative = $_.FullName.Substring($edugBundleRoot.TrimEnd('\').Length).TrimStart('\')
        $edugRelative -match '(?i)(^|[\\/])(\.env[^\\/]*|.*\.clixml|.*\.key|.*\.pfx|.*\.p12|id_rsa|id_ed25519)$'
    }
if ($edugForbidden) { throw 'Credential-like file detected in deployment bundle.' }

if ($PrepareOnly) {
    $edugFileCount = @(Get-ChildItem -LiteralPath $edugBundleRoot -Recurse -Force -File).Count
    Write-Output "PREPARED: sanitized production bundle with $edugFileCount files. No upload performed."
    return
}

Push-Location $edugBundleRoot
try {
    & railway up --detach --json `
        --project $edugProject `
        --environment $edugEnvironment `
        --service $edugService `
        --message 'Production API release after verified schema and runtime security'
    if ($LASTEXITCODE -ne 0) { throw 'Railway production upload failed.' }
} finally {
    Pop-Location
}
