# ResearchMind AI — Comprehensive Project Document

ResearchMind AI is an autonomous multi-agent research orchestration platform. It allows users to input any research topic, automatically maps the scope, queries search networks, crawls and indexes web sources, scores reliability, checks for factual contradictions, extracts research gaps, drafts a markdown document with inline citations, generates a slide deck, and streams progress updates in real-time.

---

## 1. System Architecture

Below is the layout of the multi-agent orchestration and database RAG system:

```mermaid
graph TD
    User([User Request]) --> NextJS[Next.js Frontend]
    NextJS -->|REST API Post| FastAPIRouter[FastAPI Router]
    FastAPIRouter -->|Background Task| LangGraph[LangGraph State Machine]

    subgraph LangGraph Orchestration
        Planner[Planner Agent] --> Researcher[Researcher Agent]
        Researcher --> Critic[Critic Agent]
        Critic --> Writer[Writer Agent]
        Writer --> Reviewer[Reviewer Agent]
        Reviewer -->|Review Failed & Iteration < 3| Planner
        Reviewer -->|Review Passed / Max Iterations| End([Research Complete])
    end

    Researcher -->|Scrapes Web & Crawls Content| Web[Tavily Search API]
    Researcher -->|Vector Embedding Generation| EmbeddingService[HuggingFace Embeddings]
    EmbeddingService -->|384-dim Vectors| DB[(Neon PostgreSQL + pgvector)]

    UserPDF[User PDF Upload] -->|Extract Text & Chunk| PDFPlumber[pdfplumber Service]
    PDFPlumber --> EmbeddingService
    
    End -->|Compile Data| DB
    End -->|Generate Presentation| PPTXGen[PowerPoint pptx Generator]
    
    LangGraph -->|Real-time Events| WSManager[WebSocket Connection Manager]
    WSManager -->|Live Timeline Update| NextJS
```

---

## 2. Key Features: Implementation & Working

### 2.1 Multi-Agent Research Scoping (LangGraph Orchestrated)
The core of ResearchMind AI is a stateful multi-agent system built using **LangGraph**. The shared context between agents is managed via `ResearchState`, which acts as the single source of truth.

#### 1. Planner Agent
*   **File Path**: [planner.py](file:///d:/auto/backend/app/agents/planner.py)
*   **Implementation**: Prompted Llama-3.3-70b-versatile via Groq APIs, utilizing LangChain's `.with_structured_output()` constraint mapping to a Pydantic `PlannerOutput` schema.
*   **Working**: Receives the user's research topic. Decomposes it into 3–5 high-level research objectives, 4–7 focused subtopics, and 8–15 searchable questions (2–3 per subtopic) optimized for search indexing.
*   **Fallback**: If the LLM call fails, the node returns a set of generic fallback objectives and standard query items to prevent pipeline crashes.

#### 2. Researcher Agent
*   **File Path**: [researcher.py](file:///d:/auto/backend/app/agents/researcher.py)
*   **Implementation**: Tavily Client SDK, localized `HuggingFaceEmbeddings` utilizing the `all-MiniLM-L6-v2` transformer model (384 dimensions).
*   **Working**: Iterates through each planned search query in parallel, fetching the top 10 search results per query from Tavily including raw page contents. For each unique URL:
    1. The raw page content is chunked into overlapping blocks (size: 400 characters, overlap: 80 characters).
    2. Chunks are converted into 384-dimensional vector embeddings in a background thread pool.
    3. The chunks and corresponding embeddings are saved temporarily in the state to be persisted later.

#### 3. Critic Agent
*   **File Path**: [critic.py](file:///d:/auto/backend/app/agents/critic.py)
*   **Implementation**: Custom domain scoring heuristics and pairwise LLM factual analysis.
*   **Working**:
    1. **Source Reliability Scorer**: Automatically scores incoming sources. Domains matching high-trust patterns (e.g., `.gov`, `.edu`, `arxiv.org`, `nature.com`) receive a `0.90` reliability score. Low-trust keywords (e.g., `reddit`, `quora`, `blog`) receive `0.40`. Standard domains default to `0.65`. Sources scoring below `0.45` are discarded.
    2. **Contradiction Detector**: Compares the top 5 verified sources pairwise (capping at 6 pairs to minimize API calls). A prompt instructs the Llama model to look for factual contradictions between claims in the source excerpts. Any contradictions are saved alongside resolution/reconciliation tips.

#### 4. Writer Agent
*   **File Path**: [writer.py](file:///d:/auto/backend/app/agents/writer.py)
*   **Implementation**: Keyword-based source ranking (RAG context assembly) + sequential LLM section generation.
*   **Working**:
    *   Iterates through each subtopic defined by the Planner.
    *   Scores verified sources based on keywords matching the subtopic and builds a localized context from the top 5 source excerpts.
    *   Resolves citation indexing systematically (offsets indices between sections to prevent key collision).
    *   Sends a prompt to the LLM to draft a structured Markdown section (300-500 words) using only the provided context. Inline citation references like `[1]` are enforced.
    *   **Rate-Limit Management**: Inserts an `await asyncio.sleep(3)` delay between sections to prevent hitting the Groq 6000 TPM (tokens per minute) rate limits on free-tier API keys.
    *   Generates an executive abstract and appends a bibliography list.

#### 5. Reviewer Agent
*   **File Path**: [reviewer.py](file:///d:/auto/backend/app/agents/reviewer.py)
*   **Implementation**: Quantitative heuristics combined with qualitative LLM feedback.
*   **Working**:
    *   Analyzes the first 2000 characters of the report draft.
    *   Extracts research gaps (identifies subtopics not covered and evidence of lack).
    *   Calculates a **Base Confidence Score** mathematically based on the number of reliable sources (caps at 10) and total citations (caps at 15) weighted with the average reliability score of indexed references.
    *   Queries Llama to rate the report and blends the LLM score (60%) with the quantitative base score (40%) for the final project confidence rating.
    *   **Conditional Loop Edge**: If `review_passed` is `False` and current iteration < `3`, the LangGraph router redirects the state back to the Planner node to re-evaluate the scope. Otherwise, the graph terminates.

---

### 2.2 Database & Vector Search Infrastructure
*   **File Paths**: [database.py](file:///d:/auto/backend/app/database.py) | [models.py](file:///d:/auto/backend/app/models.py) | [schemas.py](file:///d:/auto/backend/app/schemas.py)
*   **Implementation**: Neon PostgreSQL cloud database, async SQLAlchemy engine, and the **pgvector** database extension.
*   **Working**:
    *   SQLAlchemy models define the data structure. The application automatically initializes the database tables during startup if they do not exist.
    *   FastAPI dependencies inject an `AsyncSession` into API endpoints, automatically performing a transaction commit on success and rollback on exceptions.
    *   Vector fields of 384 dimensions are defined directly on database tables using `Vector(384)`, enabling vector operations directly inside the Postgres layer.

---

### 2.3 Real-Time Updates & WebSocket Brokerage
*   **File Path**: [ws.py](file:///d:/auto/backend/app/api/ws.py)
*   **Implementation**: FastAPI WebSocket routing, python native asyncio queues, and a global connection repository mapping project identifiers to active client connections.
*   **Working**:
    *   A WebSocket path `ws://127.0.0.1:8000/api/v1/ws/{project_id}` is exposed for client connections.
    *   During execution, agent nodes invoke the `emit_agent_event` helper, transmitting state updates (e.g., `planner started`, `researcher searching`, etc.) to the connection broker.
    *   The manager broadcasts the updates as JSON to all listening client sockets.
    *   If an event is a "started" status, the manager automatically updates the project's state column in the DB to keep the REST APIs synchronized.
    *   A keep-alive ping loop runs every 15 seconds to prevent browser sockets from closing due to inactivity.

---

### 2.4 Reference Material Upload & Local PDF RAG Ingestion
*   **File Path**: [uploads.py](file:///d:/auto/backend/app/api/uploads.py)
*   **Implementation**: `pdfplumber` library, sentence-transformers vector generation, and async DB inserts.
*   **Working**:
    *   Accepts multipart PDF file uploads.
    *   Uses `pdfplumber` to extract clean text page-by-page.
    *   Splits pages into overlapping text chunks.
    *   Calculates 384-dimensional dense vectors using the HuggingFace embedding pipeline.
    *   Creates a `Source` entry (type="pdf", default reliability=0.85).
    *   Saves the chunks in the `document_chunks` table linked to the source. These chunks become immediately searchable in the project's vector database, allowing the Writer to incorporate them into the final report.

---

### 2.5 Dynamic Presentation Slide Deck Generator
*   **File Path**: [pptx_generator.py](file:///d:/auto/backend/app/services/pptx_generator.py)
*   **Implementation**: `python-pptx` layout builder, regular expression string cleaning.
*   **Working**:
    *   Invoked automatically at the end of a successful LangGraph run.
    *   Constructs a professional, dark-themed 16:9 widescreen presentation slide deck using custom layout dimensions.
    *   Auto-extracts key sentences from the generated Markdown text of each section using regex patterns to format as bullet points on respective slides.
    *   Generates slides sequentially:
        1.  **Title Slide**: Widescreen title, metadata statistics, and confidence score.
        2.  **Objectives**: Bullet points detailing research goals.
        3.  **Scope**: Lists the subtopics covered in the report.
        4.  **Content Slides**: One slide per subtopic with extracted bullet points.
        5.  **Research Gaps**: Highlights areas lacking literary evidence.
        6.  **References**: Lists up to 10 indexed sources and their reliability scores.
    *   Saves the presentation to disk (`reports/`) and records the path in the `Report` table for client download.

---

### 2.6 Frontend User Interface & Layout
*   **File Paths**: [page.js](file:///d:/auto/frontend/src/app/page.js) | [page.js](file:///d:/auto/frontend/src/app/research/%5Bid%5D/page.js) | [globals.css](file:///d:/auto/frontend/src/app/globals.css)
*   **Implementation**: Next.js App Router (React), Vanilla CSS, inline SVG icon assets.
*   **Working**:
    *   **Landing Page**:
        *   Checks backend health via `/health` to verify api server status.
        *   Includes a centered search bar for starting new research projects.
        *   Displays recent projects list with real-time status badges and deletion triggers.
    *   **Research Workspace (Dashboard)**:
        *   Uses a split-pane layout: the left pane contains a tabbed system (Report, Sources, Contradictions, Gaps, Graph), while the right pane houses the WebSocket timeline feed and the PDF document upload dropzone.
        *   **Sources Tab**: Displays indexed articles, showing source type, fetched timestamp, and reliability scores color-coded in green, yellow, or red.
        *   **Contradictions Tab**: Compares conflicting claims side-by-side with resolution guidance.
        *   **Gaps Tab**: Details areas that lack sufficient evidence.
        *   **Graph Tab**: Dynamically visualizes the research hierarchy, showing subtopics linked to their respective questions.
        *   **Live Timeline**: Automatically appends and logs agent milestones, automatically scrolling to remain pinned to the latest event.

---

## 3. Database Schema

ResearchMind AI manages 6 tables via the async SQLAlchemy Declarative system:

### 1. `projects`
Stores information about the top-level research sessions.
*   `id` (UUID, Primary Key): Unique project identifier.
*   `topic` (String(512)): The user's input research statement.
*   `subtopics` (JSONB, Nullable): List of planned subtopics.
*   `research_questions` (JSONB, Nullable): List of research queries.
*   `status` (String(64)): Current pipeline stage (`pending`, `planning`, `researching`, `critiquing`, `writing`, `reviewing`, `done`, `failed`).
*   `confidence_score` (Float, Nullable): The final reliability score computed by the Reviewer.
*   `created_at`/`updated_at` (DateTime): Auditing timestamps.

### 2. `sources`
Tracks references retrieved from Tavily or uploaded by the user.
*   `id` (UUID, Primary Key): Unique source identifier.
*   `project_id` (UUID, Foreign Key → `projects.id`): Associated project.
*   `title` (String(512)): The page or document title.
*   `url` (Text, Nullable): Web page URL (null for uploaded files).
*   `source_type` (String(32)): Source origin (`web`, `pdf`, `paper`, `news`).
*   `reliability_score` (Float, Nullable): The reliability score (0.0 to 1.0) computed by the Critic.
*   `justification` (Text, Nullable): Reasoning behind the reliability score.
*   `fetched_at` (DateTime): Timestamp of when the source was indexed.

### 3. `document_chunks`
Stores text chunks and vector embeddings for semantic search.
*   `id` (UUID, Primary Key): Unique chunk identifier.
*   `source_id` (UUID, Foreign Key → `sources.id`): Associated source document.
*   `content` (Text): The raw text chunk.
*   `embedding` (Vector(384)): 384-dimensional dense vector embeddings generated by HuggingFace.
*   `page_number` (Integer, Nullable): Page number (for PDF uploads).
*   `chunk_index` (Integer): Ordering index.

### 4. `contradictions`
Records factual contradictions identified between source documents.
*   `id` (UUID, Primary Key): Unique contradiction identifier.
*   `project_id` (UUID, Foreign Key → `projects.id`): Associated project.
*   `claim_a` (Text): Factual statement from Source A.
*   `source_a_id` (UUID, Foreign Key → `sources.id`): Reference source A.
*   `claim_b` (Text): Factual statement from Source B.
*   `source_b_id` (UUID, Foreign Key → `sources.id`): Reference source B.
*   `explanation` (Text): Reasoning behind the contradiction.
*   `resolution_tip` (Text): Resolution guidance.

### 5. `research_gaps`
Tracks research areas that lack sufficient evidence.
*   `id` (UUID, Primary Key): Unique gap identifier.
*   `project_id` (UUID, Foreign Key → `projects.id`): Associated project.
*   `gap_title` (String(256)): Brief summary of the gap.
*   `description` (Text): Details of the missing information.
*   `evidence` (Text): Explanation of the lack of evidence.

### 6. `reports`
Stores the final generated report and export file paths.
*   `id` (UUID, Primary Key): Unique report identifier.
*   `project_id` (UUID, Foreign Key → `projects.id`, Unique): Associated project.
*   `markdown_content` (Text): The full Markdown report draft.
*   `citations` (JSONB): Mapping of citation indices to references.
*   `pptx_file_path` (Text): Path to the generated presentation file on disk.
*   `created_at` (DateTime): Timestamp of when the report was compiled.

---

## 4. File Structure

```
d:/auto/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── critic.py        # Reliability heuristics & pairwise contradiction detection
│   │   │   ├── graph.py         # LangGraph state & flow definitions
│   │   │   ├── llm.py           # LLM and embedding client singletons
│   │   │   ├── planner.py       # Research scoping and question planning
│   │   │   ├── researcher.py    # Tavily Web searches & Local RAG chunking
│   │   │   └── reviewer.py      # Quality review, gap analysis, and confidence rating
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py      # Projects REST API endpoints & LangGraph triggering
│   │   │   ├── reports.py       # Reports REST API endpoints & exports download
│   │   │   ├── uploads.py       # Multi-page PDF text extraction and embedding ingestion
│   │   │   └── ws.py            # WebSocket status broadcaster
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── pptx_generator.py # Python-pptx builder
│   │   ├── config.py            # Pydantic Settings configuration
│   │   ├── database.py          # SQLAlchemy async session builder
│   │   ├── main.py              # FastAPI app registration and startup hooks
│   │   ├── models.py            # SQLAlchemy database tables mapping
│   │   └── schemas.py           # Pydantic schemas (DTO structures)
│   ├── reports/                 # Holds generated PowerPoint slide files
│   ├── .env                     # App keys configuration (Groq, Tavily, PostgreSQL)
│   ├── pyproject.toml           # Python dependencies (LangChain, LangGraph, python-pptx)
│   └── alembic.ini              # Database migration configurations
│
└── frontend/
    ├── src/
    │   └── app/
    │       ├── research/
    │       │   └── [id]/
    │       │       ├── page.js          # Interactive dashboard layout
    │       │       └── page.module.css  # Dashboard localized CSS styles
    │       ├── favicon.ico
    │       ├── globals.css      # Core theme colors, font families, and animation styles
    │       ├── layout.js        # Next.js app wrapper
    │       ├── page.js          # Research scope initializer landing page
    │       └── page.module.css  # Landing page localized CSS styles
    ├── package.json             # Next.js workspace details
    └── next.config.js
```

---

## 5. Local Setup & Execution Guide

### 5.1 Prerequisites
*   Python 3.10 or higher installed.
*   Node.js v18 or higher installed.
*   PostgreSQL instance with the `pgvector` extension installed.

### 5.2 Environment Configuration
Create a `.env` file in `d:/auto/backend/` with the following variables:
```ini
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxx
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/researchmind_db
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DEBUG=True
```

### 5.3 Database Configuration
Ensure the `pgvector` extension is enabled in your database:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5.4 Backend Startup
Navigate to the backend directory, install python dependencies, and start the development server:
```powershell
# Navigate and create virtual environment
cd d:/auto/backend
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e .

# Run FastAPI Server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The interactive Swagger API documentation will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 5.5 Frontend Startup
Navigate to the frontend directory, install npm packages, and run the Next.js development server:
```powershell
cd d:/auto/frontend

# Install dependencies
npm install

# Run Next.js
npm run dev
```
Open your browser and navigate to: [http://127.0.0.1:3000](http://127.0.0.1:3000).
