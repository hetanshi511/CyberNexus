# CyberNexus

## Overview

CyberNexus is an AI-powered multi-agent marketplace designed to automate cybersecurity, recruitment, content analysis, and productivity workflows through specialized intelligent agents integrated into a single platform.

The platform provides a centralized environment where users can access multiple AI agents, each designed to perform a specific task such as email security monitoring, resume evaluation, compliance verification, content review, presentation generation, and interview scheduling.

---

## Features

### 1. AutoPresenter Agent
- Generates professional PowerPoint presentations from topics or structured JSON data.
- Supports charts, tables, and formatted slides.

### 2. DB Presenter Agent
- Converts natural language questions into SQL queries.
- Retrieves data from PostgreSQL.
- Generates presentation-ready reports with visualizations.

### 3. Content Reviewer Agent
- Crawls websites and analyzes content.
- Detects grammar, spelling, punctuation, and typographical errors.

### 4. Header Validator Agent
- Performs website security header analysis.
- Identifies missing or vulnerable security configurations.

### 5. Resume Reviewer Agent
- Evaluates resumes against job descriptions.
- Generates candidate scores and matching reports.

### 6. Cybersecurity Newsletter Bot
- Collects recent cybersecurity news.
- Generates AI-powered newsletter content.
- Supports automated posting workflows.

### 7. Compliance Verification Agent
- Fetches Jira tickets.
- Analyzes compliance alignment.
- Generates structured compliance reports.

### 8. Email Security Agent
- Monitors Gmail inboxes in real time.
- Detects phishing, spam, and fraud emails.
- Uses VirusTotal and AI-based analysis.

### 9. Interview Scheduler Agent
- Integrates with Google Calendar.
- Finds available interview slots.
- Creates meeting invitations and sends notifications.

---

## System Architecture

CyberNexus follows a modular multi-agent architecture consisting of:

- Frontend Layer
- Backend API Layer
- Agent Orchestrator
- AI Processing Layer
- External Service Integrations
- PostgreSQL Database
- Authentication Layer

### Core Components

- Frontend Application
- Backend Services
- Agent Orchestrator
- LangGraph Workflows
- LLM Processing Engine
- PostgreSQL Database
- Firebase Authentication

---

## Technology Stack

| Technology | Purpose |
|------------|----------|
| Python | Backend Development |
| LangChain | LLM Integration |
| LangGraph | Agent Workflow Management |
| PostgreSQL | Database Management |
| Firebase Authentication | User Authentication |
| Gmail API | Email Processing |
| Google Calendar API | Scheduling |
| Jira API | Compliance Analysis |
| VirusTotal API | Threat Detection |
| Docker | Containerization |
| HTML/CSS/JavaScript | Frontend Development |

---

## Security Features

- Firebase Authentication
- Token-Based Authorization
- Multi-Tenant Architecture
- HTTPS Communication
- OAuth-Based API Access
- Secure Environment Variables
- User Data Isolation

---

## Project Structure

```text
CyberNexus/
│
├── Backend/
│   ├── Agents/
│   ├── Services/
│   ├── Workflows/
│   └── APIs/
│
├── frontend/
│
├── docs/
│
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL
- Docker (Optional)
- Firebase Project
- API Credentials:
  - Gmail API
  - Google Calendar API
  - Jira API
  - VirusTotal API

### Clone Repository

```bash
git clone https://github.com/hetanshi511/CyberNexus.git
cd CyberNexus
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file:

```env
DATABASE_URL=
OPENAI_API_KEY=
FIREBASE_CONFIG=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GOOGLE_CALENDAR_CREDENTIALS=
JIRA_API_TOKEN=
VIRUSTOTAL_API_KEY=
```

### Run Application

```bash
python app.py
```

or

```bash
docker-compose up --build
```

---

## Workflow

1. User Authentication
2. Agent Selection
3. Input Validation
4. API/Data Retrieval
5. AI Processing
6. Report Generation
7. Output Delivery


---

## Contributors

- Hetanshi Patel 


