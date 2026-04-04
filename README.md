# SmartAC - Backend API

> AI-Powered Accounting Platform  

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com)
[![Claude AI](https://img.shields.io/badge/Claude-Haiku-purple)](https://anthropic.com)
[![AWS EC2](https://img.shields.io/badge/AWS-EC2-orange)](https://aws.amazon.com)

---

## Live Demo

| Service | URL |
|---|---|
| Flutter Web App | http://smartac-frontend-1775237755.s3-website.eu-west-2.amazonaws.com |
| Android | https://appdistribution.firebase.dev/i/6c2309e7959899a4 |
| iOS | iOS Link Coming Soon |

---

## What is SmartAC?

SmartAC is an AI-powered accounting platform that use an Agentic AI Architecture, to autonomously analyses financial transactions, detects anomalies, assesses risk, and generates professional accounting documents and send Email Alerts.

### Key Features

- **Fuzzy Logic Risk Scoring** - mathematically models risk across 3 dimensions (amount, vendor trust, frequency) using `scikit-fuzzy`
- **NLP Categorisation** - keyword-based transaction categorisation
- **Junior Assist** - Claude AI agent that categorises individual transactions
- **Reviewer Assist** - Claude AI agent that reviews batches and flags concerns
- **Orchestrator Agent** - autonomous Sense -> Plan -> Act -> Report cycle
- **Generative AI** - produces client letters and anomaly reports
- **Email Alerts** - automatically emails high-risk alerts via Gmail SMTP
- **GDPR Audit Trail** - every AI decision is logged

---

## Architecture

```
backend/
├── core/
│   ├── config.py          # environment variables
│   ├── database.py        # SQLAlchemy engine + session
│   ├── claude.py          # Claude API client
│   └── email.py           # Gmail SMTP email service
│
├── features/
│   ├── transactions/
│   │   ├── models.py      # SQLAlchemy Transaction model
│   │   ├── schemas.py     # Pydantic request/response
│   │   ├── repository.py  # database queries
│   │   ├── service.py     # fuzzy logic + NLP
│   │   └── router.py      # HTTP endpoints
│   │
│   ├── agents/
│   │   ├── schemas.py     # request/response models
│   │   ├── service.py     # Claude AI agents
│   │   └── router.py      # agent endpoints
│   │
│   ├── orchestrator/
│   │   ├── schemas.py
│   │   ├── service.py     # Sense -> Plan -> Act -> Report
│   │   └── router.py
│   │
│   ├── documents/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   └── router.py
│   │
│   └── audit/
│       ├── models.py
│       ├── schemas.py
│       ├── repository.py
│       └── router.py
│
├── db/
│   └── seed.py            # 50 mock transactions
├── main.py
├── requirements.txt
└── Dockerfile
```

**Design pattern:** Feature-first clean architecture - each feature owns its models, schemas, repository, service, and router. Mirrors the Flutter app's BLoC/Cubit layer structure.

---

## Fuzzy Logic Risk Engine

The risk engine uses `scikit-fuzzy` to implement a fuzzy inference system with 3 inputs and 9 rules:

```
Inputs:
  amount        (£0 -> £10,000)   low / medium / high
  vendor_trust  (0.0 -> 1.0)      low / medium / high
  frequency     (0.0 -> 1.0)      rare / moderate / frequent

Rules:
  IF amount=HIGH    AND vendor_trust=LOW    -> risk=HIGH
  IF amount=HIGH    AND frequency=RARE      -> risk=HIGH
  IF vendor_trust=LOW AND frequency=RARE   -> risk=HIGH
  IF amount=MEDIUM  AND vendor_trust=LOW   -> risk=MEDIUM
  ...

Output:
  risk_score  (0–100)
  risk_label  low (<35) / medium (35–64) / high (≥65)
  xai_explanation  (plain English reason)
```

---

## Orchestrator Agent - Sense -> Plan -> Act -> Report

```
SENSE  -> reads all transactions, counts unprocessed/high-risk/anomalies
PLAN   -> autonomously decides which agents to run
ACT    -> executes: fuzzy scoring -> junior assist -> reviewer -> reports -> email
REPORT -> returns full structured result with action log
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/transactions` | List all transactions |
| GET | `/transactions/stats` | Dashboard statistics |
| POST | `/transactions/analyse-all` | Run fuzzy risk scoring |
| POST | `/agents/junior-assist` | AI categorisation |
| POST | `/agents/reviewer-assist` | Batch AI review |
| POST | `/agents/orchestrate` | Full autonomous run |
| POST | `/agents/generate-letter` | Generate client letter |
| POST | `/agents/generate-anomaly-report` | Generate anomaly report |
| GET | `/agents/documents` | List all documents |
| GET | `/agents/audit-log` | GDPR audit trail |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.11) |
| Database | SQLite (SQLAlchemy ORM) |
| AI Model | Claude Haiku (Anthropic) |
| AI Model | Ollama for local machine |
| Fuzzy Logic | scikit-fuzzy + numpy |
| HTTP Client | httpx (async) |
| Email | Gmail SMTP (smtplib) |
| Server | Uvicorn (ASGI) |
| Hosting | AWS EC2 t3.small (eu-west-2) |

---

## Local Setup

```bash
# 1. Clone and enter backend
cd backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your keys

# 5. Run
uvicorn main:app --reload
```

Visit **http://localhost:8000/docs** for the interactive API documentation.

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite:///./accountiq.db
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_EMAIL=alerts@yourdomain.com
```

---

## Deployment

```bash
# Deploy backend to EC2
cd ~/smart_ac_backend
bash copy_backend.sh 00.000.000.000

# Reset database if schema changed
ssh -i ./smartac-key.pem ec2-user@00.000.000.000 \
  "rm -f /app/accountiq.db && sudo systemctl restart smartac"
```

---

## AWS Infrastructure

| Resource | Detail |
|---|---|
| EC2 | t3.small, eu-west-2 |
| OS | Amazon Linux 2023 |
| Service | systemd `smartac.service` |
| S3 | Static Flutter web hosting |
| Cost | ~£12/month running, ~£0.50/month stopped |

---
