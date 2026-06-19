# Security Policy & Hardening Framework

Welcome to the Silentra Infrastructure Security Guide. This document defines our security baselines, product version management lifecycle, and our Coordinated Vulnerability Disclosure (CVD) process.

## Supported Software Boundaries

We provide security maintenance windows exclusively for current-generation relational infrastructure branches. Legacy document-store paradigms have reached End-Of-Life (EOL).

| Version | Status | Architectural Engine | Maintenance Level |
| :--- | :---: | :--- | :--- |
| 2.0.x | ✅ Active | Supabase / PostgreSQL | Mainstream Patches & Vulnerability Audits |
| 1.0.x | ❌ EOL | MongoDB Document Paradigm | None (Deprecation Complete) |

---

## Threat Model & Security Baseline Controls

To maintain compliance and protect end-user PII (Personally Identifiable Information) across corporate Discord instances, the platform adheres to the following paradigms:

### 1. Privilege Minimization
The Bot requires administrative permission bounds *only* inside designated support category wrappers. Global guild permissions should be restricted to the minimum required scopes: `Manage Channels`, `View Channels`, `Send Messages`, and `Embed Links`.

### 2. Administrative Token Rotation
Our database interactions leverage the administrative `service_role` JWT. If an orchestration vector or server log reveals this token:
1. Immediately access the Supabase Management Console.
2. Navigate to `Project Settings` -> `API`.
3. Trigger an **API Key Rotation** event.
4. Update the production `.env` container environment variable and issue a `pm2 restart silentra-ticket-core` command.

---

## Coordinated Vulnerability Disclosure (CVD)

If you discover a critical zero-day exploit, privilege escalation vector, SQL Injection (SQLi) loophole, or arbitrary command execution vulnerability within this application, **do not file a public issue on the GitHub tracker.**

### Reporting Pipeline
Please transmit a encrypted or detailed security brief directly to our Infrastructure Operations Team via the designated corporate support channels or project administrator contact vectors.

**Your report should ideally contain:**
* A comprehensive summary of the vulnerability class.
* Step-by-step instructions to achieve a Proof of Concept (PoC).
* Any relevant trace details or environment specificities.

### Our Commitment
* **Triage Phase:** Within 24-48 business hours, our core developers will validate the exploit vector.
* **Remediation Phase:** A hotfix will be developed internally and deployed across active branches without public disclosure of the underlying code structure until the risk is mitigated.
* **Safe Harbor:** We pledge not to initiate legal or administrative actions against security researchers who responsibly report flaws in accordance with this document.