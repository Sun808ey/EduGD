# EDUGD data protection and retention controls
This document is the operational boundary for the administrator panel. It is
not legal advice and does not replace the school's Personal Data Protection
Office (PDPO) registration or certificate review before real learner data is
processed.

## Data minimisation

- Use the school asset number and device UUID; do not identify an individual
  learner in an asset or assignment record.
- Assign shared devices to a class or department. The assignment API rejects
  any target type other than `class` or `department`.
- No learner photographs, private device content, health information, family
  information, or personal telephone contacts are accepted by the panel.
- DPC evidence stores privacy-safe control results. Browsing history is not an
  accepted evidence payload.

## Access and transport safeguards

- Administrator routes require an active authenticated session and the
  relevant role permission; asset correction and retention redaction use the
  existing `policy.manage` role.
- Production API and frontend origins must be HTTPS. The development profile
  permits loopback HTTP only.
- Administrator passwords are stored as password verifiers, never plaintext.
- Administrative corrections and redactions record the operator, operation,
  changed field names, reason, and timestamp without copying old personal
  values into the audit record.

## Corrections and retention

Use `PATCH /admin/devices/{device_uuid}/asset` to correct an asset and
`PATCH /admin/devices/{device_uuid}/location-assignments/{assignment_uuid}` to
correct an assignment. Both require a reason and are audited.

Set `DEVICE_RETENTION_DAYS` to the school's approved retention period. Once a
device is retired and the window has elapsed, an authorised administrator can
call `POST /admin/devices/{device_uuid}/data-retention/purge` with a reason.
The operation removes asset identifiers, notes, and assignment rows while
retaining the non-personal device UUID and immutable audit evidence needed to
explain the redaction. It is irreversible and should be approved under the
school's retention schedule.

Set `AUDIT_RETENTION_DAYS` to the approved audit-log retention period (the
default is 3,650 days). The value is bounded at application startup; any
deletion or archival of immutable audit evidence must be a separately reviewed
retention operation and must preserve the evidence-chain requirements.

Backups must follow the reviewed migration runbook: encrypt independent
copies, restrict access, verify a restore, and retain them only for the
approved operational and legal period. No hosted migration or backup action is
performed by this change.
