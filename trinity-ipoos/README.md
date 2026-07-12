# Trinity Intelligence — IPOOS (IPO Operating System)

> **Building the AI Operating System for India's Capital Markets.**

---

## 🏢 Brand Overview & Core Positioning

**Trinity Intelligence** is a state-of-the-art enterprise AI platform designed to automate and streamline the Initial Public Offering (IPO) preparation process. Its core product, **IPOOS (IPO Operating System)**, is specifically tailored for Indian Small and Medium Enterprises (SMEs) to navigate the rigorous compliance requirements of the **SEBI (Issue of Capital and Disclosure Requirements) Regulations, 2018 (ICDR 2018)**.

By integrating structured data intake, real-time validation checks, and AI-assisted drafting, IPOOS reduces the time-to-draft for Draft Red Herring Prospectus (DRHP) documents from months to days, ensuring maximum precision and full regulatory alignment.

---

## 🚀 Key Features & Modules

### 1. Multi-Step React Intake Wizard
An intuitive, step-by-step UI wizard designed for issuers, advisors, and merchant bankers to input critical data across key categories:
*   **Company Setup**: Define corporate metadata, exchange targets (e.g., NSE Emerge, BSE SME), and regulatory identifiers (CIN).
*   **Objects of the Issue**: Categorize fresh issue and Offer for Sale (OFS) amounts, use of proceeds (Capex, Debt repayment, General Corporate Purposes), and justification rules.
*   **Capital Structure**: Manage pre-IPO shareholding, promoter groups, and lock-in requirements.
*   **Related Party Transactions (RPT)**: Document cross-holdings, director conflicts, and transaction values.
*   **Litigation**: Track active cases against the company, promoters, and directors, distinguishing between material civil litigation and criminal cases.
*   **Financials**: Multi-year balance sheet inputs, P&L metrics, and key performance indicators.

### 2. SEBI ICDR 2018 Rules Engine (Validator)
A robust rules engine running cross-section and completeness validations:
*   **Completeness Rules**: Ensures no fields are left blank, tagging missing fields with placeholders.
*   **GCP Limits**: Enforces SEBI rules (e.g., General Corporate Purposes amount cannot exceed 25% of the total fresh issue size).
*   **Promoter Contribution Check**: Validates if promoter holding meets minimum lock-in guidelines.
*   **Materiality Thresholds**: Tags and validates litigation items that exceed material thresholds.

### 3. Automated Drafting Engine
Generates regulatory-compliant narrative sections for the DRHP using Generative AI (LLM integration):
*   **Validation Flag Enforcement**: Refuses to generate drafts if there are unresolved **Blocking** validation flags.
*   **Caveat Integration**: Appends warnings (e.g., "RPT exceeds 10% of revenue") as caveats to the prompt for LLM consumption.
*   **Placeholder Formatting**: If data is missing but the flag is non-blocking (e.g., Warning), embeds `[MISSING: <field_name>]` placeholders to preserve formatting without breaking draft creation.

---

## 🛠️ Technology Stack

*   **Frontend**: Next.js (App Router), React, TypeScript, TailwindCSS/Vanilla CSS, Pnpm Workspaces.
*   **Backend**: Python, Django REST Framework (DRF), PostgreSQL.
*   **Cache & Message Queue**: Valkey (Redis-compatible cache) and RabbitMQ.
*   **Containerization**: Docker & Docker Compose.

---

## 📂 Repository Structure

```
.
├── apps/
│   ├── api/                   # Django Backend API
│   │   └── plane/trinity/     # Trinity/IPOOS Core Django App (Models, Views, Validators, Drafting)
│   └── web/                   # Next.js Frontend App
│       └── app/.../trinity/   # Trinity React Wizard & Dashboard Components
├── packages/
│   ├── constants/             # Workspace constants and navigation config
│   └── i18n/                  # Multi-language translation locales (en/)
├── docker-compose-local.yml   # Dev Stack Docker services
├── docker-compose-test.yml    # Pytest execution Docker environment
└── .gitignore                 # Local-level git ignores
```

---

## ⚙️ Local Development Setup

### Prerequisites
*   Docker and Docker Compose installed.
*   Node.js (v18+) and `npm` installed.

### 1. Initialize Configuration
From this directory:
```bash
./setup.sh
```
This generates local configuration `.env` files for the services.

### 2. Run the Local Backend Services
```bash
docker compose -f docker-compose-local.yml up -d
```

### 3. Run Backend Unit Tests
To run Pytest within the contained Docker test network:
```bash
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/trinity/tests/
```

### 4. Run Frontend Development Server
From this folder:
```bash
npx pnpm install
npx pnpm run dev
```

---

## 📤 Push to GitHub Guide

To push this sub-directory as a standalone repository:

### 1. Configure Your Git Identity (if needed)
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 2. Add and Commit All Files
```bash
git add .
git commit -m "Rebrand to Trinity Intelligence IPOOS and add module"
```

### 3. Link Your GitHub Repository and Push
Create a repository on GitHub (e.g. `trinity-ipoos`), copy its remote URL, and run:
```bash
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

---
*Developed by Trinity Intelligence Team.*
