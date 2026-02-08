# ChiefOps — Step Zero: Documentation Suite

> **An AI-powered Chief Operations Officer agent** — part of the YENSI AI Platform

---

## What is ChiefOps?

ChiefOps is an AI-powered COO assistant that works from raw file dumps (Slack exports, Jira CSV, Google Drive files) and uses AI to piece together the real state of operations — people, projects, risks, and opportunities.

**Step Zero** is the foundational release: Extract → Analyze → Recommend. No live API integrations, no authentication, no multi-tenancy. Just a COO, their data, and an intelligent agent.

---

## Document Index

| # | Document | Description |
|---|----------|-------------|
| 00 | **README** (this file) | Documentation suite overview and index |
| 01 | [Product Requirements](./01-PRD.md) | Complete PRD with features, NFRs, success criteria, and phasing roadmap |
| 02 | [System Architecture](./02-ARCHITECTURE.md) | Container topology, service interactions, Docker Compose structure, API design |
| 03 | [Data Models](./03-DATA-MODELS.md) | All 15 MongoDB collections with Pydantic v2 schemas, indexes, and relationships |
| 04 | [Memory System](./04-MEMORY-SYSTEM.md) | Three-layer conversational memory: hard facts, compacted summaries, recent turns |
| 05 | [Citex Integration](./05-CITEX-INTEGRATION.md) | RAG backbone integration — what gets indexed, query patterns, client implementation |
| 06 | [AI Layer](./06-AI-LAYER.md) | Adapter pattern, CLI and OpenRouter implementations, prompt templates, structured output |
| 07 | [Report Generation](./07-REPORT-GENERATION.md) | NL-triggered reports, report spec JSON, templates, NL editing, PDF export pipeline |
| 08 | [File Ingestion](./08-FILE-INGESTION.md) | Slack/Jira/Drive parsers, file type detection, deduplication, ingestion pipeline |
| 09 | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | People identification, cross-source entity resolution, role detection, COO corrections |
| 10 | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | Dashboard architecture, layouts, widget spec, NL management, grid system |
| 10B | [Widget Types & Components](./10B-WIDGET-TYPES-AND-COMPONENTS.md) | 10 widget types reference, data query engine, React components, Zustand stores |
| 11 | [Implementation Plan — Part A](./11-IMPLEMENTATION-PLAN.md) | Repo structure, Docker Compose, Sprints 0-5 |
| 11B | [Implementation Plan — Part B](./11B-IMPLEMENTATION-PLAN-CONTINUED.md) | Sprints 6-9, testing strategy, risk management, deployment guide |
| 12 | [UI/UX Design](./12-UI-UX-DESIGN.md) | Page layouts, wireframes, color palette, component library, responsive design |

---

## Technology Stack

As mandated by [technical.md](../technical.md):

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, MongoDB (Motor), Pydantic v2, pytest |
| Frontend | React 19, Vite, TypeScript strict, Tailwind CSS, Zustand, Axios |
| AI (Dev) | Claude CLI, Codex CLI, Gemini CLI (subprocess) |
| AI (Prod) | Open Router |
| RAG | Citex (Qdrant + MongoDB + Neo4j + MinIO) |
| Infrastructure | Docker & Docker Compose |
| Ports | Sequential from 23000 (10 services) |

---

## Quick Start

```bash
git clone <repo-url> yensi-chiefops
cd yensi-chiefops
cp .env.example .env
docker compose up -d
# Frontend: http://localhost:23000
# Backend:  http://localhost:23001/docs
```

---

## Port Allocation

| Service | Port |
|---------|------|
| Frontend | 23000 |
| Backend (FastAPI) | 23001 |
| MongoDB | 23002 |
| Redis | 23003 |
| Citex API | 23004 |
| Citex Qdrant | 23005 |
| Citex MongoDB | 23006 |
| Citex MinIO | 23007 |
| Citex Neo4j | 23008 |
| Citex Redis | 23009 |

---

## Key Design Principles

1. **NL-First** — Everything through conversation except file upload and settings
2. **File Dump Only** — No live API integrations in Step Zero
3. **AI Adapter Pattern** — Abstract interface, concrete implementations per provider
4. **Citex as RAG Backbone** — ChiefOps never builds its own RAG pipeline
5. **No Authentication** — Single-user, local Docker deployment
6. **Vertical Feature Slices** — Each sprint delivers end-to-end working functionality

---

## Related

- [YENSI AI Platform Technical Standards](../technical.md)
