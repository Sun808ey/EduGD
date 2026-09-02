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
Flask Backend ─────► PostgreSQL (Neon)
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
| Database         | PostgreSQL / Neon         |
| Android          | Kotlin + Android DPC      |
| Rate limiting    | Redis                     |
| Backend hosting  | Render                    |
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
├── backend/       # Flask REST API
├── frontend/      # React + Vite administrator dashboard
├── androidDPC/    # Android device policy agent
├── .github/       # CI/CD workflows
├── docs/          # Project documentation
├── render.yaml    # Render deployment configuration
└── README.md
```

## Development

### Backend

```powershell
cd backend
python -m pytest
```

### Frontend

```powershell
cd frontend\school-policy-admin
npm install
npm run dev
```

### Android

Open `androidDPC/` in **Android Studio** and build/run the Android DPC according to the project documentation.

## Deployment

* **Frontend:** Vercel
* **Backend:** Render
* **Database:** Neon PostgreSQL
* **Rate limiting:** Redis

Production secrets must be supplied through environment configuration and **must never be committed to Git**.

## Project Status

**Project type:** Final-year academic Proof-of-Concept MVP
**Target environment:** Ugandan secondary schools
**Target devices:** School-owned Android devices
**Degree:** Bachelor of Science in Computer Security and Forensics

