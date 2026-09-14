# Zero-cost Redis setup: steps 1 and 2

Status: **Upstash staging assignment, external TLS endpoint, synthetic probe
writes and Railway staging Redis retirement explicitly approved. Upstash Free database
created; owner reports the staging live probe PASS. Approved Railway staging
Redis service and volume retirement is dashboard-verified. One Aiven Free Valkey
production service, external TLS and temporary verification writes are explicitly
approved; Aiven production is Running on Free-1. Certificate and hostname
verification passed over TLS 1.3; the owner reports the production authenticated
compatibility probe PASS. Both local provider probes have now passed.
Step 3 remains paused.** Updated 14 September 2026.

## Decision and constraints

Use distinct hosted stores for staging and production. Both must have an
explicit $0 plan, separate credentials, verified TLS and compatibility with the
backend's installed Redis protocol client and rate-limiter library. Do not use
trial credits as evidence of ongoing zero cost, create duplicate accounts to
bypass limits, share a store through different key prefixes, or weaken TLS.

The approved assignments are **Upstash Free for staging** and **Aiven Free
Valkey for production**. Upstash staging is explicitly approved and provisioned; Aiven production
was created on Free-1 on 14 September 2026. Valkey is a Redis-compatible alternative, not Redis itself; the
actual pinned client/library combination must pass the live probe before use.

| Candidate | Free offering and limitations | Decision |
| --- | --- | --- |
| Upstash Free | One Free database; 256 MB, 500,000 monthly commands, 10 GB monthly bandwidth; TLS supported | Proposed staging store; verify Free eligibility in the owner's account [1][2] |
| Aiven Free Valkey | One service of this type per organization; single node, 1 GB RAM, maxmemory 50%, backups; no credit card needed or time limit | Created on Free-1; owner-reported production compatibility probe PASS [3] |
| Redis Cloud Free | Free Essentials does not support TLS | Rejected for external connections; no plaintext credentials over the public network [4] |
| Railway Redis | Existing staging Redis consumes metered resources, even while idle | Not accepted as the ongoing zero-cost Redis design; do not add production Redis there |

Upstash's pricing page has an ambiguous general FAQ saying ten databases can be
created for free, while its Free-plan comparison specifies one Free database.
This plan relies on the explicit one-Free-database allowance, not on assuming
ten independently free stores. Never enter payment details: the pricing page
says doing so upgrades a Free database to pay-as-you-go.[1]

Aiven Free includes TLS but is not aimed at production workloads.[9]
It has no SLA or VPC, does not let the operator select the region, and
may stop inactive services. Upstash Free also has usage limits and inactivity
archiving. Neither plan supports a claim of uninterrupted or flawless production
availability. Public authenticated TLS endpoints replace Railway-private Redis
networking; that architecture change needs explicit approval.[2][3][5][6]

Zero provider charges do not prove zero total application cost. Connections from
Railway to these providers can consume Railway egress allowance. Actual command
volume, network usage, latency, Free-plan enforcement and account eligibility
must be verified before accepting the whole deployment as sustainable at $0.
No paid tier, paid backup, private-link add-on or automatic upgrade is authorized.

## Prepared compatibility check

The backend pins `redis==6.4.0`, `limits==5.8.0` and `Flask-Limiter==4.1.1`.
Production startup/readiness already use `Redis.from_url(...).ping()` and accept
`rediss://` URLs. These code facts indicate a possible integration path; they do
not constitute a live test of either provider. Aiven's migration guidance covers
Valkey/Redis client differences; Upstash documents Lua scripting support.[7][8]

`scripts/verify_redis_service.py` uses those installed Redis and limits packages.
It requires an explicit write opt-in and a separately pinned expected hostname.
It requires certificate and hostname verification, rejects plaintext URLs and
URL query overrides, and checks:

- TLS/authenticated PING.
- A random synthetic value written with a 60-second TTL and read back.
- Actual fixed-window rate limiting: first two hits allowed, third denied.
- Counter inspection and deletion of only this run's keys, with TTL cleanup if
  the connection is lost. It never flushes a database or enumerates user keys.

Supply secrets privately to the process through `REDIS_PROBE_URL`; supply the
approved hostname through `REDIS_PROBE_EXPECTED_HOST`. If needed, use an approved
local CA file via `REDIS_PROBE_CA_FILE`. Do not paste secrets into commands, chat,
Git or reports. For the current redis-py client, the URL must use `rediss://`;
an Aiven `valkeys://` URI must be adapted to that TLS scheme while retaining the
same endpoint and credentials. Never replace it with plaintext `redis://`.

After approval, from `backend`, run with secrets already securely supplied:

```powershell
venv/Scripts/python.exe -m scripts.verify_redis_service --environment staging --approve-probe-writes
```

After staging has passed, set the independently approved production endpoint and
run the same command with `--environment production`. The environment flag is a
report label, not automatic credential selection. Verify both pinned hosts and
provider IDs belong to the intended accounts and differ before running.

Only temporary synthetic probe data is sent. No app secrets, Supabase URLs,
production rows, client identifiers or existing Redis data are transferred.
Probe output suppresses provider exceptions because they can contain secrets.

Six local safety regression checks passed (target/TLS rejection before network
access, write opt-in and exception redaction). **The owner subsequently reported
both staging and production live probes PASS.**
A successful local test is not proof of hosted compatibility, network access
from Railway, quota adequacy or cross-environment isolation.

## Ordered implementation gates

1. **Step 1: staging replacement.** Explicit approval for Upstash Free, its
   external TLS endpoint and the synthetic probe has been received. The owner signs in or
   creates the account and accepts any terms personally. Confirm an unused Free
   database allowance and create `edug-redis-staging`, explicitly on Free with no
   payment details or auto-upgrade. Record the non-secret database ID, hostname,
   region and plan. Run the compatibility probe with staged credentials. Check
   quota enforcement and expected usage. Resolve failures before step 2.
2. **Retire metered staging Redis after replacement verification.** The owner
   explicitly approved retirement of Railway service
   `f189c590-df15-4297-9286-1afa643a171f` and deleting its volume
   `1ba54880-ce0f-4abb-bd94-fa89d9bdf68b`. Verify it contains no required data.
   Volume deletion is irreversible; stopping compute alone does not remove
   storage consumption. Keep the resource map's actual state until removal is
   confirmed. Retirement was applied and verified on 13 September 2026: both
   resources are absent after reloading staging, with no pending-change banner.
3. **Step 2: production store.** Only after step 1 passes and separate approval,
   the owner establishes an Aiven account and confirms its unused Free Valkey
   allowance. Create `edug-redis-production` on the permanent Free plan, not a
   paid-plan trial. Record the provider ID/host and plan; run the production
   probe with its own credentials. Verify both stores are distinct and that
   TLS works from the intended Railway environment before declaring integration
   complete. Probe execution from Railway requires its own approved runner
   configuration; neither API is to be deployed merely to obtain a test result.
4. **Stop before step 3.** Report every passed and pending gate. Keep both API
   services offline and Supabase untouched. No Vercel work, app deployment,
   database migration, commit or push is authorized by this plan.

Existing Railway staging Redis and its volume have been retired after the
owner-reported replacement probe passed. The earlier step-2 proposal to
provision Railway production Redis is superseded by this zero-cost-only plan.

## Staging verification and retirement checkpoint

The owner completed sign-in. Created `edug-redis-staging` in the Personal account
on the selected Free plan; the creation review showed monthly $0 and TLS. No
payment method was added. Dashboard details:

- Database ID: `5c8b39a5-c1f5-4a0d-923b-a9bebb84374e`.
- TCP endpoint: `set-mayfly-105830.upstash.io`, port `6379`.
- Region: Ireland, `eu-west-1`.
- Plan: Free Tier; TLS/SSL enabled. Eviction was left disabled.

**Completed: the owner reported `PASS: staging TLS/auth, expiry and fixed-window checks.`**
This is an owner-reported local probe result, not an agent-observed test or a
Railway-to-Upstash connectivity test. The command used for this checkpoint is
retained below for an explicitly authorized repeat if needed.
No credential was printed or saved to the repository. The probe now supports
hidden terminal input, so the URL need not appear in shell history or process
arguments. In an interactive terminal from `backend`, run:

```powershell
venv/Scripts/python.exe -m scripts.verify_redis_service --environment staging --expected-host set-mayfly-105830.upstash.io --approve-probe-writes --prompt-url
```

At the hidden prompt, supply the database's TCP connection URL using `rediss://`
(with username, password, the endpoint above and port 6379). Do not supply the
REST HTTPS endpoint, a redis-cli command, or a read-only token. Do not paste the
URL in chat. Share only the PASS/FAIL result. The script refuses hidden-input mode
without an interactive terminal rather than risking echoed credentials.

The local six safety tests, Ruff and type checking passed before this handoff.
Following the owner's live PASS, the approved Railway service and volume were
deleted. The final Railway confirmation listed exactly `edug-redis-staging`
and `redis-volume-Zt_B` in `blissful-luck/staging`. Reloading the staging
architecture showed only the offline API, with neither Redis resource nor a
pending-change banner. No required application data had been assigned to this
temporary Redis; neither API had been connected to it.
Both API services remain unconfigured by this step. Aiven production and step 3
remain untouched. Approvals persist; no repeat approval is needed for the same
Upstash setup, synthetic probe or identified Railway retirement scope.

**Production approval received on 13 September 2026:** one Aiven Free Valkey service named
`edug-redis-production`, using its authenticated external TLS endpoint and
short-lived synthetic verification writes. Confirm the account's permanent
Free allowance before creation; no paid trial, upgrade, payment method or API
deployment is included. The owner must personally complete sign-in and any
account terms. Production provisioning has not started. Provider limits,
representative usage and Railway egress still need validation before any
claim of sustainable zero-cost application operation.

**Historical sign-in checkpoint (13 September):** the Aiven console opened at
`https://console.aiven.io/login` and requires authentication. The owner must sign
in (or sign up and personally complete any account terms), then confirm the
console is ready. Do not add payment details or create a paid trial service.
After sign-in, inspect the organization's unused Free Valkey allowance, select
the permanent Free plan, review the service name and price, and create only the
approved service. Record its non-secret identity and endpoint before the
production probe. This same scope does not require repeat approval. No Aiven
service, credential change or API deployment was performed at this checkpoint.
Official Free-tier terms were rechecked on 13 September 2026: no credit card or
time limit, one Free Valkey per organization, no SLA and possible inactivity
power-off remain documented.[3][9]

The owner subsequently reported sign-in at `/welcome`. In the connected Chrome
Sun profile, the available Aiven tab still showed an email-verification-required
message; opening `/welcome` returned to `/login`. An authenticated console is
therefore not yet accessible to the agent. Complete verification and sign-in in
the connected profile, or identify the browser/profile containing the signed-in
session. No service was created and the existing approval remains valid.

**Onboarding checkpoint (14 September 2026, subsequently completed):** the authenticated `/welcome` page
is now accessible in Chrome Sun. Valkey is selected with the displayed Free
plan: 1 CPU, 1 GB RAM, auto-assigned cloud in Europe, monthly cost Free and
"Free forever. No credit card required." The page also advertises trial
credits, but the selected service plan is Free, not a paid trial plan.
Prepared project name `edug-production` and service name `edug-redis-production`.
Creation has not been submitted: the required personal name is blank and the
country default needs owner confirmation. The owner has been asked for these
details; do not infer them from the email address or local timezone. Service
identity, endpoint and live verification remain pending. Approval persists.

## Aiven production creation result

On 14 September 2026, entered the owner-supplied onboarding details and created
only `edug-redis-production` in project `edug-production`. The creation screen
showed monthly cost Free and Free forever; persisted service settings confirm
**Free-1 (1 CPU, 1 GB RAM, backups for disaster recovery)**. The separate platform
trial banner applies to non-free services; no paid service, payment method or
upgrade was selected.

- Organization/account ID: `a5dea12e0be4` (My Organization).
- Service identity: project `edug-production`, service `edug-redis-production`.
- Created: 14 September 2026, 03:35 UTC.
- Provider/region: DigitalOcean, `ams` (Amsterdam, Netherlands).
- Version: Valkey 9.1.1, one node (verified after startup).
- Endpoint: `edug-redis-production-edug-production.a.aivencloud.com:22050`.
- Settings: `valkey_ssl` enabled; public internet, default IP allowlist open to
  all; no static IPs. No API credential or application data was attached.
- Current status: Running; Free-1 confirmed after refresh. Owner-reported authenticated probe PASS on 14 September 2026.

The production hostname differs from the Upstash staging hostname. This proves
distinct endpoint assignments, not full credential or application isolation.
An initial certificate-only connection attempt could not resolve the new host
during provisioning. After startup, a direct connection passed certificate-chain
and hostname verification using the default system trust store and TLS 1.3.
This agent-observed handshake did not authenticate or write keys. No additional
CA file was required for this handshake.

**Completed manual checkpoint:** the owner ran the production probe with private
URI entry and reported PASS on 14 September 2026. Command retained for reference
(run from `backend`; no repeat is currently required):

```powershell
venv/Scripts/python.exe -m scripts.verify_redis_service --environment production --expected-host edug-redis-production-edug-production.a.aivencloud.com --approve-probe-writes --prompt-url
```

Privately copy the service URI from Aiven Connection information and change only
its `valkeys://` scheme to `rediss://` for the pinned Redis client. Keep the
credentials, hostname and port intact. Supply it only at the hidden prompt and
share only PASS/FAIL. Do not disable certificate verification. If the provider
requires a CA file, keep it outside Git and supply `REDIS_PROBE_CA_FILE`.
Neither API has been deployed; step 3 remains paused.

## Redis checkpoint audit, 14 September 2026

The owner reported `PASS: production TLS/auth, expiry and fixed-window checks.`
This is an owner-reported local probe result, alongside the earlier staging
PASS. The agent independently verified the production TLS handshake and service
Running/Free-1 settings; it did not observe the authenticated probe execution.

Completed: separate Upstash Free staging and Aiven Free-1 production resources,
local TLS/authentication, TTL and fixed-window checks reported PASS for both,
and approved retirement of the Railway staging Redis service and volume.
No secret values were supplied in the result or recorded in this document.

Remaining before full integration acceptance: verify connectivity from each
intended Railway environment, matching credential scope and API references,
representative command/memory/egress usage within Free allowances, and deployed
application isolation. Neither API is configured or deployed by this checkpoint.
Provider provisioning and local compatibility checks are complete; this does
not establish flawless end-to-end operation or sustainable whole-app zero cost.
Step 3 remains paused. No migration, Git commit or push was performed.

## Sources

1. Upstash, [Redis pricing](https://upstash.com/pricing/redis), accessed 13 September 2026.
2. Upstash, [Security](https://upstash.com/docs/redis/features/security), accessed 13 September 2026.
3. Aiven, [Valkey Free tier](https://aiven.io/docs/products/valkey/concepts/valkey-free-tier), updated 13 March 2026.
4. Redis, [TLS support](https://redis.io/docs/latest/operate/rc/security/database-security/tls-ssl/), accessed 13 September 2026.
5. Aiven, [Get started with Valkey](https://aiven.io/docs/products/valkey/get-started), accessed 13 September 2026.
6. Upstash, [Frequently asked questions](https://upstash.com/docs/redis/help/faq), accessed 13 September 2026.
7. Aiven, [Python Redis-to-Valkey migration](https://aiven.io/developer/python-valkey-redis-migration), accessed 13 September 2026.
8. Upstash, [Lua key locking](https://upstash.com/docs/redis/features/key-locking), accessed 13 September 2026.
9. Aiven, [Free Tier](https://aiven.io/free-tier), TLS, no automatic charges and workload limitations; accessed 13 September 2026.
