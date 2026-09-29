# Retired empty-schema migration entry point.
#
# Production contains live administrator and audit data. This wrapper exists
# only to prevent an operator from accidentally running the former fresh-install
# procedure. The reviewed path is run_live_production_upgrade.ps1, which checks
# the approved starting revision, a verified restore rehearsal, the maintenance
# window, and the production advisory lock before it permits DDL.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$message = 'This empty-schema migration runner is retired. Use ' +
    'scripts/run_live_production_upgrade.ps1 with its required backup-and-restore ' +
    'attestation during the approved maintenance window.'
throw $message
