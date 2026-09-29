# Run under the same Windows account as the local Codex workspace.
# Never print the entered URL, password, or provider exception text.
param([switch]$FromClipboard)

$ErrorActionPreference = 'Stop'
$edugBackend = Split-Path -Parent $PSScriptRoot
$edugPython = Join-Path $edugBackend 'venv\Scripts\python.exe'
$edugDestination = Join-Path $edugBackend 'operator-evidence\production-migration-url.clixml'
$edugValidation = @'
import os
from pathlib import Path
from app.config import validate_postgres_database_uri, database_project_identity
raw = os.environ.pop('EDUG_HANDOFF_INPUT', '')
if not raw.startswith(('postgresql://', 'postgresql+psycopg2://')):
    print('Not saved: enter the complete PostgreSQL URL, starting with postgresql:// or postgresql+psycopg2://.')
    raise SystemExit(2)
try:
    url = validate_postgres_database_uri('MIGRATION_DATABASE_URL', raw)
    assert database_project_identity(url) == 'hszskxrgkptbytuquyfu'
    assert url.username in ('postgres', 'postgres.hszskxrgkptbytuquyfu')
    assert url.password and url.database == 'postgres'
    assert url.query.get('sslrootcert') and Path(url.query['sslrootcert']).is_file()
except Exception:
    print('Not saved: check production project, owner role, password encoding, database postgres, port 5432, sslmode=verify-full and existing sslrootcert path.')
    raise SystemExit(2)
print('PASS: local production URL checks. No database connection was made.')
'@

if (-not (Test-Path -LiteralPath $edugPython)) { throw 'Backend Python environment is missing.' }
Push-Location $edugBackend
try {
    & git check-ignore --quiet -- $edugDestination
    if ($LASTEXITCODE -ne 0) { throw 'Handoff destination is not Git-ignored.' }
    if ($FromClipboard) {
        $edugClipboardText = Get-Clipboard -Raw
        if ([string]::IsNullOrWhiteSpace($edugClipboardText)) { Write-Output 'Not saved: clipboard is empty. Copy the complete URL and retry.'; return }
        $edugInput = ConvertTo-SecureString -String $edugClipboardText.Trim() -AsPlainText -Force
        $edugClipboardText = $null
    } else { $edugInput = Read-Host 'Paste the complete production migration-owner PostgreSQL URL (hidden)' -AsSecureString }
    $edugPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($edugInput)
    try { $env:EDUG_HANDOFF_INPUT = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($edugPointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($edugPointer) }
    & $edugPython -c $edugValidation
    if ($LASTEXITCODE -ne 0) { Write-Output 'Input was rejected. The existing encrypted file was not changed.'; return }
    New-Item -ItemType Directory -Path (Split-Path -Parent $edugDestination) -Force | Out-Null
    $edugInput | Export-Clixml -LiteralPath $edugDestination
    Write-Output 'SAVED: validated input encrypted for this Windows account. No migration performed.'
    if ($FromClipboard) {
        try { Set-Clipboard -ErrorAction Stop; Write-Output 'Clipboard cleared.' }
        catch { Write-Warning 'The encrypted file is saved, but clipboard cleanup failed. Copy harmless text to replace the URL; do not re-enter the credential.' }
    }
} finally {
    Remove-Item Env:EDUG_HANDOFF_INPUT -ErrorAction SilentlyContinue
    $edugClipboardText = $null
    if ($edugInput) { $edugInput.Dispose() }
    Pop-Location
}
