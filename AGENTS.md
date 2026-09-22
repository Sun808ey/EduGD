# Working instructions

- Do not commit or push changes unless the user explicitly overrides this
  instruction. Complete the requested edits and verification, suggest a commit
  message, and leave committing to the user.
- When a required manual configuration step is reached, explain the concrete
  step and pause until the user confirms it is complete. If no manual step is
  required, proceed to complete the task.
- Before any explicitly authorized commit, inspect the staged file list and
  staged diff or run a secret scan of the staged content. Never print secret
  values in reports or tool output. Keep local credentials, private keys,
  database dumps, operator evidence and local certificates out of Git.
- A public Supabase CA may be staged only after individual review under
  `backend/docs/database-migration-runbook.md`; do not broadly allow certificates.

- Use Free-tier resources only. Approved hosted Supabase projects are staging
  `dviuaqtlbuefmfmswwqt` and production `hszskxrgkptbytuquyfu`; do not create a
  third project or run destructive integration tests against either. Follow
  `backend/docs/environment-resource-map.md`. Obtain explicit approval before
  provider configuration, deployments, migrations or credential changes. Do not
  enable paid plans, add-ons or billable overages without an explicit override
  of the Free-only constraint.
