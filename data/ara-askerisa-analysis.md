# ARA / AskERISA — Slack Channel Analysis Report

**Channel:** #ara-askerisa | **Period:** Dec 11, 2025 → Feb 4, 2026 | **486 messages, 9 users**

---

## 1. Project Overview

**AskERISA** (aka "ARA" / "Askerisa") is an **AI-powered chatbot** built for the **American Retirement Association (ARA)**. It answers questions about **ERISA** (Employee Retirement Income Security Act) — a complex body of U.S. federal law governing retirement plans and employee benefits.

The chatbot acts as an **AI paralegal** (explicitly NOT a lawyer) that helps ARA's advisors quickly find answers from the **ERISA Outline Book** (~11,000 pages across multiple chapters). Previous vendors failed because they used fully automated AI approaches that couldn't handle the deeply nested legal document structure.

**Client:** Darren (ARA side) | **Dev team:** DevPixel | **Lead:** Aris Lancrescent

### Tech Stack

| Component | Technology | Hosting |
|-----------|-----------|---------|
| Frontend | React (static) | Firebase Hosting (Blaze Plan) |
| Backend | Node.js / Express.js | Render.com |
| Database | Firestore | Google Cloud |
| AI/LLM | OpenAI GPT-4.1 | OpenAI API |
| Vector Store | OpenAI Vector Store | OpenAI |
| UI Rendering | React Markdown | — |

### Live URLs

- **ARA chatbot:** `https://ara-askerisa.web.app/v1`
- **ARA admin panel:** `https://ara-askerisa-admin.web.app/`
- **Demo site (Chapter 6 only):** `https://askerisa-447c5.web.app/`
- **Dev instance admin:** `https://ask-erisa-dev-admin.web.app/`
- **Dev instance chatbot:** `https://ask-erisa-dev.web.app/`

---

## 2. Features Discussed

### A. Core RAG (Retrieval-Augmented Generation) Pipeline

**Status: Working, refinements ongoing**

4-step process:

1. Submit user query to get top_k matches from the vector store
2. Use matches and metadata to trace back to the original document
3. Use original document to rehydrate the matches (expand context)
4. Send rehydrated matches as context to the LLM with user query

Technical details:
- Endpoint: `POST https://api.openai.com/v1/responses`
- Vector search returns 10 chunks; filtered by score threshold (currently 0.5)
- All matches with score > 0.5 are used (not just top 5)
- Uses React Markdown library for rendering responses

### B. Document Chunking (Manual Section Splitting)

**Status: All chapters uploaded**

Documents manually split by section hierarchy rather than arbitrary page/character counts. This was identified as the critical differentiator — previous vendors failed with automated chunking.

Splitting rules:
- Split by sections, up to 3 levels deep (e.g., Chapter 6, Section III, Part D)
- Only go deeper when a section is too large
- Do NOT go beyond the Part level (Part E.5.a is too deep)
- Each split file starts with the parent chain (e.g., "Chapter 6 Title\nSection I...")
- Remove document headers; keep formatting consistent
- Preambles (text before first subsection) handled as their own slice
- Appendices chunked separately
- Vector DB handles automated chunking within each split file
- Final Chapter 6 upload: 80 files
- Strict naming convention: `Chapter-17_Section-III_Part-A_Subpart-1.docx`

### C. Rehydration Logic (Context Expansion)

**Status: Basic implementation done, refinement needed**

Cascading fallback:

1. **Step 1:** Use the full matched document (already manually split)
2. **Step 2:** If too large, bounded window — 3000 chars before and after the matched chunk
3. **Step 3 (future):** Pull neighboring sections (parent section + adjacent subsections)
4. **Step 4 (future):** Summarize section and send summary + matched chunk text

Implementation details:
- Source path prepended to each context block (e.g., "Source: Chapter 7, Section V, Part C")
- When cutting off context, use closest line break for full paragraphs
- Consecutive/close chunks must be combined, not duplicated
- Overlapping contexts must be prevented (causes LLM problems)
- Footnotes are NOT automatically referenced; would need explicit rehydration logic

### D. Query Construction (QC)

**Status: Phase 1 completed; Phase 2 planned**

**Phase 1 — Unclear Concept Detection (completed):**
- LLM-based classification of user queries as CLEAR or UNCLEAR
- Extracts unclear words/phrases verbatim from the query
- Returns strict JSON: `{ "isClear": true|false, "concepts": []}`
- Delivered Jan 29 by Soheb

**Phase 2+ (planned, not yet implemented):**
1. User enters inquiry
2. Query LLM for unclear concepts
3. If unclear, send concepts to vector DB
4. Rehydrate matches
5. Send original inquiry, identified concepts, and rehydrated matches to LLM
6. LLM constructs a final enhanced query
7. Use enhanced query for actual retrieval

### E. Admin Panel

**Status: Functional**

- Upload/manage document chunks
- Chunks displayed and sortable by name
- ARA branding applied (no background image)
- Chapter name and description fields for each uploaded document
- **Missing:** "insert chunk" capability to add a single file without re-uploading entire chapter (~2 hours estimated)

### F. Chat UI / Landing Page

**Status: Functional with improvements**

Changes completed:
- Landing page: left-aligned text, full width
- Response page: removed upper right buttons, added paragraph/list separation
- Text load speed resolved — moved from direct Firebase frontend fetch to backend endpoint (~5s → ~1s)
- Descriptions generated via ChatGPT (not just first paragraph)
- UI cloned from DevPixel website

### G. Conversation History / Context Management

**Status: Not yet implemented** — mentioned as future need

### H. Token Management

**Status: Partially implemented**

- MAX_CONTEXT_CHARS = 500,000
- Cascading fallback from full document to bounded window
- Needs to handle: multiple matches, overlapping contexts, conversation history
- Quota exhaustion encountered during testing

### I. Tone Configuration

**Status: Aris handling personally** — configurable via admin panel; responses initially too verbose

---

## 3. Task Assignments

### Aris Lancrescent — Project Lead / Director
- Defines technical architecture and rehydration approach
- Liaises with client (Darren) for access, permissions, feedback
- Reviews all deliverables and test responses
- Personally handles tone configuration
- Reviews document splitting quality
- Demonstrated to ARA business (received "pleasantly surprised" feedback)

### Bindu Guduru — Project Manager / Team Lead
- Day-to-day team management
- Environment setup (Firebase, Render, OpenAI)
- Produces status updates for Aris
- Managed document splitting and file organization
- Performed manual Chapter 6 section splitting with Aris's guidance
- Coordinated upload of all ERISA chapters (80+ files)
- Created architecture summary document
- Assigned tasks (ARA-4, ARA-5) to Naresh
- Created QC Phase 1 timeline/deliverable document

### Srini Chinta — Senior Developer / Architect
- Infrastructure guidance (Render, Firebase, Express)
- Resolved IAM/permission issues with Firebase (datastore.databases.create)
- Provided pseudo-code for rehydration logic
- Raised concerns about token exhaustion with large chunks
- Discussed parsing vs. summarization approaches with Aris

### Naresh Daravath — Backend Developer
- Built initial AI integration (corrected from wrong approach to Aris's 4-step spec)
- Worked on Firestore chunk storage structure
- Assigned ARA-4 (Firestore chunk storage) and ARA-5 (neighboring section rehydration)
- Had personal emergencies requiring time off

### Soheb Mohammad — Developer
- Implemented neighbor-inclusion logic for rehydration
- Resolved Firebase text load speed issue
- Implemented QC Stage 1 (unclear concept detection) — delivered Jan 29
- Handled overlapping chunk scenarios
- Re-uploaded corrected chapters (3B, 14)
- Deployed latest code to Render

### Sharvil Kotian — UI Developer
- Assigned UI adjustments: landing page, response page, admin screen

### Yashmit Mykala — Document Processing
- Performed document chunk splitting (Chapter 6 sections 3, 4, 7)

### abhishek reddy
- **No visible activity or direct assignments** (mentioned indirectly by Bindu regarding database response speed)

### Surya
- **No visible activity or assignments** (joined channel only)

---

## 4. Missing Pieces / Gaps

### Unresolved Decisions

1. **Score threshold (0.5) is a placeholder** — needs systematic tuning, no plan for when/how
2. **Summarization layer** — explicitly deferred ("entire new meta layer"), no timeline
3. **Sophisticated neighboring section logic** — current approach is simple order-based; hierarchy-aware approach not implemented
4. **Chunk merge distance** — Aris said chunks within "X distance" should be combined; X not defined
5. **Footnote handling** — acknowledged AI can't automatically find related footnotes; no plan established
6. **Dev vs. Demo vs. Prod confusion** — "Prod" clarified to mean "demo site"; no true production environment

### Tasks Mentioned But Not Assigned

1. Apply rehydration logic to DevPixel's own website
2. QC Phase 2+ implementation (full query enhancement pipeline)
3. "Insert chunk" admin feature (~2 hours, no decision made)
4. Chapter name/description updates in admin panel
5. Migration to ARA's own GCP infrastructure

### Open Questions Never Answered

1. How will the system handle queries spanning **multiple chapters**?
2. How will **conversation history** be incorporated into the pipeline?
3. What happens when **all chapters are loaded** and retrieval noise increases?
4. What is the plan for **v2** (expanding to all advisors)?
5. What about **references and indices** mentioned as v2 features?

### Dependencies That Could Block Progress

1. **ARA's GCP permissions** — spent days resolving IAM issues; migration to ARA's infrastructure could resurface problems
2. **OpenAI quota limits** — already encountered quota exhaustion during testing; will worsen as more chapters load
3. **Document quality** — inconsistent formatting (manual tabs, no defined heading levels, irregular nesting) limits automated processing

---

## 5. Key Decisions Made

| # | Decision |
|---|----------|
| 1 | AI role is **paralegal, NOT lawyer** |
| 2 | **Manual document splitting** required — automated chunking fails on these legal texts |
| 3 | Develop on **DevPixel's instance first**, migrate to ARA later |
| 4 | **Clone DevPixel website** as starting point |
| 5 | Upload as **Word docs, not HTML** (documents lack consistent heading structure) |
| 6 | Do NOT subdivide beyond **3 levels** deep |
| 7 | Skip the **Index document** (not useful for AI) |
| 8 | **3000 chars** before/after for bounded window rehydration |
| 9 | **0.5 score threshold** for chunk filtering (temporary) |
| 10 | Firebase latency resolved via **backend endpoint** instead of direct frontend reads |
| 11 | Skip dev verifications; **upload directly to demo** for speed |
| 12 | Run both automated and manual rehydration versions **in parallel** for comparison |

---

## 6. Architecture

```
User → React Frontend (Firebase Hosting)
         │
         ▼
    Express.js Backend (Render.com)
         │
         ├──► OpenAI Vector Store (semantic search, top-K)
         │         │
         │         ▼
         │    Matched chunks + scores (filtered > 0.5)
         │         │
         ├──► Firestore (document metadata, chunks, hierarchy)
         │         │
         │         ▼
         │    Rehydration: source lookup + context expansion
         │         │
         ├──► OpenAI GPT-4.1 (chat completions)
         │         │
         │         ▼
         │    Generated response
         │
         ▼
    React Frontend (React Markdown rendering)
```

### Environments

| Environment | Purpose | URLs |
|-------------|---------|------|
| Dev | Development/testing | `ask-erisa-dev.web.app`, `ask-erisa-dev-admin.web.app` |
| Demo | Client-facing demo (Chapter 6 tuned) | `askerisa-447c5.web.app` |
| Main | Working version with all chapters | `ara-askerisa.web.app/v1`, `ara-askerisa-admin.web.app` |
| ARA's GCP | Client's own infrastructure | Not yet migrated |

### Key Technical Constraints

- **LLM context window limits:** Large sections (e.g., 104 pages) frequently exceed limits; bounded-window approach mitigates this
- **Document structure inconsistency:** Documents lack programmatic structure beyond 3 levels; manual intervention required at every stage
- **Token budgeting:** MAX_CONTEXT_CHARS = 500,000; must account for multiple matched chunks, rehydrated contexts, conversation history, and query
- **Legal precision matters:** 402f vs 402(f) are legally distinct concepts; the AI correctly distinguishes them

### Files/Resources Referenced

- **ARA ERISA.zip** — 16.5MB document corpus (pinned in channel)
- **Ask ERISA Testing Model with Sources.xlsx** — Test questions with expected answers
- **ARA Document Repository:** `drive.google.com/drive/folders/1G0PlrlYO-wBv_rVLzgedZpVOQv31TIay`
- **Vector store:** `vs_695ccbe819608191bbeec1bd013a1fd8` ("Ask-Arisa vector store")
