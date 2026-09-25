# Sunbird AI translation integration

EduGD uses Sunbird AI only as a presentation dependency for public marketing
copy and approved administrator dynamic content. The supported language codes
are exactly `eng`, `ach`, `lgg`, `teo`, `nyn`, and `lug`.

`SUNBIRD_API_TOKEN` is a Flask/Railway-only secret. It must never be placed in
Vite variables, React code, browser requests, Android DPC code, fixtures,
responses, or logs. `SUNBIRD_API_BASE_URL` defaults to
`https://api.sunbird.ai` and is accepted only as an HTTPS URL without embedded
credentials, query strings, or fragments.

The public endpoint accepts only an approved marketing `content_key` and a
supported target language:

`POST /api/v1/public/translation/translate`

The authenticated administrator endpoint accepts bounded approved dynamic
text:

`POST /api/v1/admin/translation/translate`

Successful translations are stored in `translation_cache_entries`, keyed by
source language, target language, and the SHA-256 hash of NFC-normalized source
text. PostgreSQL transaction advisory locks serialize cache misses across
backend instances. Provider failures are not cached; public pages retain their
canonical English text.

Cache rows are marked `machine` initially. The schema also permits `reviewed`
and `approved` quality states for future human review workflows.
