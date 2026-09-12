# Android Offline-First School-Owned Phone-Use Policy Enforcement System

### A Local Context-Based Proof-of-Concept MVP for Ugandan Secondary Schools

A final-year Bachelor of Science in Computer Security and Forensics project developing a **security-by-design and forensically verifiable Android offline-first phone-use policy enforcement system** for **school-owned Android devices in Ugandan secondary schools**.

## Overview

The system enables authorised school administrators to:

* Enrol and manage school-owned Android devices
* Create and assign phone-use policies
* Enforce policies offline on Android devices
* Synchronise policies and device status
* Monitor usage and compliance
* Review security-relevant audit records
* Verify selected audit information for forensic purposes

The system is designed specifically as a **local-context Proof-of-Concept Minimum Viable Product**, not as a full commercial MDM platform.

## Architecture

```text
Administrator
     │
     ▼
React + Vite Dashboard
     │ HTTPS / REST API
     ▼
Flask / Gunicorn on Railway ─────► Supabase PostgreSQL
     │
     └──────────────► Redis
     │
     ▼
Android DPC Agent
     │
     ▼
Local Offline Policy Enforcement
```

## Technology Stack

| Layer            | Technology                |
| ---------------- | ------------------------- |
| Frontend         | React + TypeScript + Vite |
| Backend          | Python + Flask            |
| Database         | Supabase PostgreSQL       |
| Android          | Kotlin + Android DPC      |
| Rate limiting    | Redis                     |
| Backend hosting  | Railway                   |
| Frontend hosting | Vercel                    |
| Version control  | Git + GitHub              |

## Key Security Principles

* Security by design
* Least privilege
* Server-side authorisation
* Secure device identity
* Offline-first enforcement
* Secure policy synchronisation
* Rate limiting
* Secure secret management
* Auditability
* Forensic verifiability
* Fail-closed security controls

## Repository Structure

```text
EduGD/
├── backend/       # Flask REST API, migrations, Railway/Gunicorn configuration
├── frontend/      # React + Vite administrator dashboard
├── .github/       # CI/CD workflows
└── README.md
```

Operational and security documentation lives in `backend/docs`. Android DPC
sources are not present in this checkout; offline enforcement and device
integration remain external verification requirements.

## Development

### Backend

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest
```

Use Python 3.12. The default suite excludes live PostgreSQL tests. See
[test configuration](backend/docs/testing.md) and
[environment configuration](backend/docs/environment.md) before starting the API.

### Frontend

```powershell
cd frontend\school-policy-admin
npm ci
npm run dev
```

Use Node.js 24 and npm 11. To verify the production bundle locally:

```powershell
$env:VITE_API_BASE_URL = 'https://api.example.invalid/api/v1'
npm run build
```

The reserved example URL is only for build verification. A deployment needs
the actual HTTPS API URL. See the [frontend README](frontend/school-policy-admin/README.md)
for authentication, supported screens, browser tests and Vercel setup.

## Deployment

* **Frontend:** Vercel
* **Backend:** Railway, root `/backend`, config `/backend/railway.json`
* **Database:** Supabase PostgreSQL, direct or session-pooler connection
* **Rate limiting:** Redis

Production secrets must be supplied through environment configuration and **must never be committed to Git**.

Railway runs `flask --app run.py db upgrade` before starting
`gunicorn --config gunicorn.conf.py run:app`; readiness is `/api/v1/ready`.
Follow the [migration runbook](backend/docs/database-migration-runbook.md)
before attaching production credentials or enabling production deployments.

## Verification and readiness

GitHub Actions includes backend quality, frontend quality and a dedicated
Supabase PostgreSQL integration workflow. The latter requires the configured
`backend-integration-test` environment and an approved disposable database.

The prepared administrator portal and backend are implemented. Repository
synchronization does not establish production readiness: live PostgreSQL,
restore rehearsal, Railway/Redis/TLS/CORS and Android checks remain release
gates. See the [production integration report](backend/docs/production-integration-report.md)
and [Phase 1 synchronization report](backend/docs/phase-1-synchronization-report.md).

## Project Status

**Project type:** Final-year academic Proof-of-Concept MVP
**Target environment:** Ugandan secondary schools
**Target devices:** School-owned Android devices
**Degree:** Bachelor of Science in Computer Security and Forensics
