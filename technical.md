# Technology Stack

This document defines the **default** technologies and architectural patterns used across projects. These are guidelines that can be adjusted based on specific project requirements.

---

## Backend (Defaults)

| Category | Technology | Version/Notes |
|----------|------------|---------------|
| Language | Python | 3.11+ |
| Framework | FastAPI | Latest |
| Database | MongoDB | via Motor async driver |
| Authentication | KeyCloak | Optional - only when auth is required |
| API Documentation | OpenAPI/Swagger | Auto-generated |
| Validation | Pydantic | v2 |
| Testing | pytest, pytest-asyncio, pytest-cov | |

---

## Frontend (Defaults)

| Category | Technology | Version/Notes |
|----------|------------|---------------|
| Framework | React | 19 (or latest stable) |
| Build Tool | Vite | Latest |
| State Management | Zustand | Recommended |
| HTTP Client | Axios | with interceptors |
| Styling | Tailwind CSS | |
| Testing | Vitest, React Testing Library, Playwright | E2E |
| Type Safety | TypeScript | strict mode |

---

## AI Integration

### Development & Testing: CLI-Based Access

AI model access during development and testing is done via CLI tools, invoked as **Python subprocesses**.

| CLI Tool | Provider | Notes |
|----------|----------|-------|
| Claude CLI | Anthropic | Authenticated terminal with Claude Code |
| Codex CLI | OpenAI | OpenAI Codex access |
| Gemini CLI | Google | Gemini model access |

**Implementation:** Python subprocess calls to CLI commands, not SDK integrations.

### Production: Open Router

| Category | Technology | Notes |
|----------|------------|-------|
| Model Router | Open Router | Multi-model access for production |

### RAG System: Citex

| Category | Technology | Notes |
|----------|------------|-------|
| RAG | Citex | External plug-and-play RAG system |

All systems requiring RAG capabilities integrate with Citex as the standardized solution.

### Adapter Pattern (Mandatory)

All AI integrations **must** implement an adapter interface:

- Abstract base class/interface for AI operations
- Concrete implementations for each provider (CLI-based for dev/test, Open Router for production)
- Configuration-driven model/provider selection
- No direct coupling to specific AI providers in business logic
- Seamless switching between development (CLI) and production (Open Router) modes

---

## Infrastructure (Defaults)

| Category | Technology | Notes |
|----------|------------|-------|
| Containerization | Docker & Docker Compose | |
| Development | Hot Module Reloading | via volume mounts |
| Ports | Custom only | Sequential starting at 23000 |

---

## Port Allocation Strategy

Ports are allocated sequentially starting at **23000**, incrementing by 1 per service.

**Example allocation:**

| Service | Port |
|---------|------|
| Frontend | 23000 |
| Backend | 23001 |
| MongoDB | 23002 |
| Redis | 23003 |
| KeyCloak | 23004 |
| KeyCloak Postgres | 23005 |

**Never use default ports** (3000, 5000, 8000, 8080, 27017, 5432, etc.)

---

## Notes

- Technology choices above are **defaults** and can be overridden per project
- Only include components that are needed (e.g., skip KeyCloak if no auth required)
- The **AI Adapter Pattern is mandatory** to ensure flexibility across providers
