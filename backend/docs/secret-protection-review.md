# Pre-push secret protection review

## Verified state

Reviewed in PowerShell at `E:\EduG` on 12 September 2026, starting from
commit `57ed90b`. No commit or push was performed for this review.

`backend/.env` was already absent from Git tracking and from the local working
directory. Its most recent path history is commit `c8e56ee` (environment
configuration protection). An empty local file was restored with exclusive
creation; it contains zero bytes and is ignored. `git rm --cached backend/.env`
was unnecessary because the index already contains no such path. No existing
local credentials were overwritten, copied or printed.

The root ignore rules now cover environment files, private-key containers and
common SSH private-key names, local certificates/certificate directories,
database dumps and compressed SQL exports, SQLite sidecars, backup directories,
and operator-evidence directories at any depth. Environment examples and authored
SQL/Python migrations remain eligible for review and tracking.

There is no automatic exception for `backend/certs/supabase-ca.pem`. If deployment
later requires this public CA, review its certificate-only contents and verify
its fingerprint against the Supabase dashboard as described in the
[migration runbook](database-migration-runbook.md), then explicitly stage only
that file with `git add -f -- backend/certs/supabase-ca.pem`. Never force-add the
certificate directory or a private key.

## Verification and limits

- All 28 representative `git check-ignore --no-index` checks passed, covering
  sensitive paths and source/example paths that must remain trackable.
- All 200 tracked working-tree files (1,270,504 bytes at scan time) were read by
  a redacted pattern scan covering private-key blocks, GitHub tokens, cloud access
  keys, service secret keys, JWT literals and database/Redis credential URLs.
- The 21 URL candidates were confined to backend test fixtures. Their context
  uses placeholder projects, reserved hosts or deliberately malformed URLs.
  No private-key blocks or provider-token candidates were reported by these rules.
- The staged file list was empty. The proposed changes contain ignore rules,
  working instructions and this review; no credential-bearing file is staged.
- `backend/.env` is a zero-byte ignored local file and is not in the index.

This targeted scan is not a guarantee that no arbitrary secret exists and is
not a full Git-history scan. Historical credential remediation already documented
in the production runbook remains a separate deployment gate. No history rewrite,
secret rotation, provider configuration or certificate provisioning was needed
for this working-tree protection task.

## Before every commit

The user owns committing and pushing. Repository `AGENTS.md` records this
instruction, the requirement to wait for any necessary manual configuration,
and the staged-content review requirement for future agent work.

From the repository root, stage only reviewed paths. Then inspect the exact
staged list and diff in a private local terminal; do not paste any discovered
credentials into chat or a report:

```powershell
git status --short
git diff --cached --name-status
git diff --cached --stat
git diff --cached --check
git diff --cached
git ls-files -- backend/.env
git check-ignore -v -- backend/.env
```

The `git ls-files` command must produce no path for `backend/.env`. If it becomes
tracked again, `git rm --cached -- backend/.env` removes only the index entry
while preserving the local file. Review the resulting staged deletion. Repeat
the staged review whenever the index changes; an earlier scan does not validate
subsequently staged content. Inspect examples for populated secrets as well as
filenames: `.gitignore` does not protect already tracked files or forced additions.

## Sources

1. Git, [gitignore documentation](https://git-scm.com/docs/gitignore), accessed
   12 September 2026: ignore rules affect untracked files; `git rm --cached`
   removes a tracked file from the index.
2. Git, [git-rm documentation](https://git-scm.com/docs/git-rm), accessed
   12 September 2026: `--cached` preserves working-tree files.
3. GitHub, [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository),
   accessed 12 September 2026: review staged changes and distinguish prevention
   from historical exposure remediation.
