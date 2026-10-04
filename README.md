<!-- Copyright 2027 Bodapati Bharat Chandra. All rights reserved. -->
<!-- Licensed under the Apache License, Version 2.0 | SPDX-License-Identifier: Apache-2.0 -->

<p align="center">
  <img src="extension\icons\truvanta-logo.png" alt="TruvantaAI" width="128" height="128"/>
  <h1 align="center">TruvantaAI</h1>
</p>

<p align="center">
  <a href="https://github.com/BharatChandra-sys/TruvantaAI/stargazers">
    <img src="https://img.shields.io/github/stars/BharatChandra-sys/TruvantaAI?style=for-the-badge&logo=github&color=4F46E5&labelColor=1e1e2e" alt="Stars"/>
  </a>
  <a href="https://chromewebstore.google.com/detail/factcheckai">
    <img src="https://img.shields.io/badge/Chrome-Extension-4F46E5?style=for-the-badge&logo=googlechrome&labelColor=1e1e2e" alt="Chrome Extension"/>
  </a>
  <a href="https://github.com/BharatChandra-sys/TruvantaAI/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-22c55e?style=for-the-badge&labelColor=1e1e2e" alt="License"/>
  </a>
  <a href="https://factcheckai-backend.onrender.com/health">
    <img src="https://img.shields.io/badge/API-Live-10B981?style=for-the-badge&logo=fastapi&labelColor=1e1e2e" alt="API Status"/>
  </a>
</p>

<h3 align="center">Memory-augmented, agentic fact-verification powered by RAG and multi-signal AI</h3>

<p align="center">
  <b>Open-source fake news detection with a Chrome extension, FastAPI backend, RAG pipeline, and LangGraph orchestration</b>
  <br/><br/>
  Real-time fact-checking • Persistent fact memory • Hybrid retrieval • Agentic re-search<br/>
  <b>94.2% on ISOT (TF-IDF, current deployment)</b> • <b>96.3% on fine-tuned RoBERTa held-out split</b><br/>
  Built with <b>FastAPI</b>, <b>fine-tuned RoBERTa</b>, <b>LangGraph</b>, <b>pgvector</b>, and <b>LLM ensemble</b>
</p>

---

## The Problem

Traditional fact-checking is manual and does not scale to the volume of content published daily. Users need a way to verify claims while browsing without leaving the page. A pure ML classifier learns patterns from training data but has no persistent memory of past verifications and no ability to reason over retrieved evidence.

## The Solution

Truvanta AI combines trained ML classifiers with a persistent knowledge base and an agentic orchestration layer. A Chrome extension sends claims to a FastAPI backend that runs a stateful LangGraph workflow — normalizing the claim, running ML models, retrieving similar historical fact-checks and evidence from a pgvector knowledge base, doing RAG reasoning over the retrieved context, and writing the result back to memory for future retrieval.

- **Owned ML intelligence** — fine-tuned RoBERTa models remain the primary classification signal
- **Persistent fact memory** — every qualified fact-check is stored with vector embeddings in PostgreSQL + pgvector, enabling semantic retrieval across restarts
- **Hybrid retrieval** — BM25 (lexical) + vector search merged with Reciprocal Rank Fusion, then cross-encoder reranked
- **RAG reasoning** — LLM reasons over retrieved evidence, not from memory; hallucinated citations are validated
- **Agentic re-search** — if initial evidence is insufficient, the workflow calls live search tools and re-evaluates
- **Calibrated meta-decision** — a trained logistic regression combines all signals; signals conflict returns `uncertain`
- **4-level ML fallback** — the system keeps working even when external services are unavailable

---

## Full Architecture

```
USER CLAIM
    |
    v
Claim Extraction + Normalization
    |
    +-----------------------------+
    |                             |
    v                             v
YOUR ML LAYER                KNOWLEDGE LAYER
    |                             |
RoBERTa-a (96.3%)            pgvector (Neon)
RoBERTa-b (79.8%)            fact_checks table
TF-IDF fallback              evidence_documents table
    |                             |
    |                        Hybrid Retrieval
    |                        BM25 + Vector
    |                             |
    |                        Cross-Encoder Rerank
    |                             |
    +-----------------------------+
                |
                v
         LangGraph Workflow
                |
    +-----------+-----------+
    |           |           |
ML Analyst  RAG Reasoner  Evidence Agent
    |           |           |
    +-----------+-----------+
                |
         Conflict Detection
         (sufficient evidence?)
                |
         +------+------+
         |             |
       YES             NO
         |             |
         |          Live Search Tools
         |          (search_news, search_web)
         |             |
         +------+------+
                |
        Manipulation Analysis
                |
         Meta-Decision Model
         (calibrated LR, 4 signals)
                |
       +--------+--------+
       |        |        |
     REAL     FAKE  UNCERTAIN
                |
         Citation Validation
                |
         Memory Write
         (VERIFIED / MODEL_ONLY / DISPUTED)
```

---

## ML Architecture — 4-Level Fallback

Every claim passes through this routing chain. Each level is tried in order; the next is used only if the previous fails.

```
Request arrives
    |
[1] Redis cache          -> instant response if seen before
    | miss
[2] ML Server 1          -> fine-tuned RoBERTa (Bharat2004/factcheckai-model-a)
    (HuggingFace Space)     96.3% accuracy on held-out split, ~1s
    | timeout / error
[3] ML Server 2          -> RoBERTa ensemble (model-a + model-b, 0.6/0.4 weight)
    (HuggingFace Space)     deployed to Bharat2004/factcheckai-model-b
    | error
[4] Local TF-IDF         -> scikit-learn Logistic Regression
                            ~50ms, always available, no external dependency
    | failure (edge case)
[5] Default 0.5          -> neutral score, surfaces as "uncertain"
```

The ML score is one signal among four in the meta-decision model. RAG provides grounded evidence context. Neither alone determines the final verdict.

---

## Key Features

### Persistent Fact Memory (pgvector)
- **fact_checks table** — every qualified result stored with 384-dim vector embedding
- **evidence_documents table** — news articles and sources stored with embeddings and source tier ranking
- **Verification status** — VERIFIED / MODEL_ONLY / HUMAN_REVIEWED / DISPUTED
- **Temporal metadata** — published_at, retrieved_at fields enable temporal reasoning (old verdict vs current truth)

### Hybrid Retrieval
- **BM25** — PostgreSQL full-text search (ts_vector) for exact phrases, entity names, dates
- **Vector search** — pgvector cosine similarity for paraphrases and conceptual similarity
- **Reciprocal Rank Fusion** — merges both ranked lists; documents appearing in both get boosted
- **Cross-encoder reranker** — ms-marco-MiniLM-L-6-v2 scores each candidate against the claim; falls back to LLM-based scoring

### Agentic RAG via LangGraph
- **FactCheckState TypedDict** — all signals flow through shared state across nodes
- **Conditional edges** — graph routes to live search if retrieved evidence is insufficient
- **RAG reasoner** — structured LLM output: assessment, supporting/contradicting evidence, citations
- **Citation validator** — checks each cited claim against retrieved source content; invalid citations suppressed
- **Memory writer** — persists result with verification status after each run

### Multi-Signal Decision Engine
- **Meta-decision model** — CalibratedClassifierCV trained to fuse ML + LLM + evidence + manipulation scores
- **Uncertainty detection** — returns `uncertain` when signals conflict or evidence balance is near 50/50
- **RAG score integration** — RAG assessment adjusts evidence score before meta-model inference
- **Manipulation scoring** — conspiracy language, emotional manipulation, cherry-picking detected independently

### Resilient Infrastructure
- **Render** — FastAPI backend (free tier, 512MB RAM)
- **Neon PostgreSQL** — serverless Postgres with pgvector, auto-resume, pgBouncer pooler
- **HuggingFace Spaces** — RoBERTa inference server (16GB RAM, free tier)
- **Startup self-healing** — on every deploy: verifies DB connection (5 retries), creates missing tables, runs Alembic migrations

---

## Architecture Components

| Component | Technology | Hosted On | Purpose |
|-----------|------------|-----------|---------|
| Chrome Extension | Vanilla JS, MV3 | Browser | UI, text selection, popup |
| Backend API | FastAPI, Python 3.11 | Render (free) | Routing, auth, LangGraph entry |
| LangGraph Workflow | langgraph 0.4.8 | In-process | Stateful fact-check orchestration |
| ML Server | RoBERTa-base, PyTorch | HuggingFace Spaces (free) | Transformer inference |
| Vector Store | PostgreSQL + pgvector | Neon (free) | Persistent embeddings + hybrid search |
| RAG Retriever | BM25 + pgvector + reranker | In-process | Hybrid retrieval pipeline |
| LLM Providers | Cerebras, Groq, Gemini, MiniMax | External APIs | Ensemble verdict + RAG reasoning |
| Evidence Search | Tavily / NewsAPI | External APIs | Live news corroboration |

### Directory Structure

```
FactCheckAI/
├── backend/
│   ├── app/
│   │   ├── analysis/       # ML, AI, evidence, manipulation, credibility
│   │   ├── retrieval/      # embeddings.py, hybrid.py, vector_store.py, reranker.py
│   │   ├── rag/            # reasoner.py, citation_validator.py
│   │   ├── agents/         # tools.py — structured agent tool definitions
│   │   ├── graph/          # state.py, nodes.py, workflow.py — LangGraph
│   │   ├── logic/          # decision.py — calibrated meta-decision model
│   │   ├── routes/         # FastAPI routers
│   │   ├── api.py          # /message — main pipeline entry
│   │   └── main.py         # lifespan, startup, middleware
│   ├── alembic/            # DB migrations (includes pgvector tables)
│   ├── data/               # model.joblib, vectorizer.joblib, meta_model.joblib
│   └── training/           # Kaggle training notebooks
├── extension/
│   ├── background/         # service_worker.js
│   ├── popup/              # popup.js, dashboard.js, history.js
│   └── content.js          # text selection tooltip
├── ml-servers/
│   └── huggingface-ensemble/   # HF Space app.py — serves model-a + model-b ensemble
├── render.yaml
└── Procfile
```

### Background Scheduler

The application runs a single background daemon thread that pings external ML services every 14 minutes (prevents HuggingFace Spaces from sleeping), checks whether training-data collection should trigger (hourly), and updates Prometheus metrics (hourly).

This is intentionally in-process rather than a separate worker because the workload is lightweight and the deployment is cost-constrained to a single free Render instance. A production-scale deployment would extract this into a dedicated scheduler service.

---

## ML Models — Training Details

Both models use the same pipeline: MinHash near-duplicate removal (threshold 0.85), 5-fold TF-IDF noise filter, Layer-wise Learning Rate Decay (decay=0.9), label smoothing 0.1, cosine LR with 6% warmup, gradient clipping 1.0, FP16 mixed precision.

| Model | Base | Training Data | Accuracy | F1 |
|-------|------|---------------|----------|-----|
| `factcheckai-model-a` | RoBERTa-base | daniB2112 (300k raw, 111k clean) | **96.3%** | **0.963** |
| `factcheckai-model-b` | RoBERTa-base | 5 mixed sources (232k raw, 103k clean) | **79.8%** | **0.790** |
| Weighted ensemble (0.6 / 0.4) | — | Combined | ~93% est. | — |

Training sources for model-b: GonzaloA/fake_news, WELFake, ErfanMoosaviMonazzah, mohammadjavadpirhadi, FEVER v1.0.

### Benchmark Results (TF-IDF + meta-model, current production)

| Dataset | Accuracy | Precision | Recall | F1 |
|---------|----------|-----------|--------|-----|
| LIAR | 68.4% | 0.67 | 0.66 | 0.66 |
| ISOT Fake News | 94.2% | 0.93 | 0.92 | 0.92 |
| FakeNewsNet | 87.3% | 0.86 | 0.85 | 0.85 |
| Custom test set | 91.5% | 0.90 | 0.89 | 0.89 |

Note: 94.2% is on ISOT using TF-IDF. 96.3% is from the fine-tuned RoBERTa model-a on its own held-out test split. These are different experiments on different datasets and are not directly comparable.

---

## Performance

```
Cache hit (repeat claim):                    < 10ms
TF-IDF only:              P50: 180ms   P95: 350ms
RoBERTa (HF Space):       P50: 1.2s    P95: 2.5s   (includes cold-start wake)
Full pipeline with RAG:   P50: 2.2s    P95: 5s
```

HuggingFace free Spaces sleep after inactivity. The background scheduler pings them every 14 minutes. Neon PostgreSQL auto-suspends and wakes in ~1s on first query.

---

## Product Evolution Plan: TruvantaAI 3.0

### Vision

Transform TruvantaAI from a pure fact-checking tool into a comprehensive research verification and literature intelligence platform. The evolution maintains fact-checking as the core product (70%) while adding academic research capabilities (30%) as an extension, operating primarily on deterministic algorithms with minimal external AI dependency.

### Core Philosophy

**Fact-Check First, Research Second**
- Maintain robust claim verification as the foundation
- Add academic paper analysis and comparison capabilities
- Operate 90-95% without external AI APIs through local-first architecture
- Provide clear provenance for every conclusion

**Intelligence Hierarchy**
```
Deterministic algorithms
    ↓
Existing retrieval systems (BM25, vector search, RRF)
    ↓
Local/open-source ML/NLP models
    ↓
Local LLM (optional)
    ↓
External AI API (fallback only)
```

### Target Architecture

```
                         TRUVANTAAI 3.0
                              |
            +-----------------+-----------------+
            |                                   |
      VERIFY ENGINE (70%)              RESEARCH ENGINE (30%)
         CORE PRODUCT                    EXTENSION LAYER
            |                                   |
    Claim verification               Paper detection & identity
    Evidence retrieval               Metadata enrichment
    Verdict calculation              Academic comparison
    Source validation                Literature patterns
    Fact-check memory                Citation intelligence
            |                                   |
            +-----------------+-----------------+
                              |
                   SHARED INTELLIGENCE
                              |
        +---------------------+---------------------+
        |                     |                     |
   Retrieval Engine      NLP/ML Layer        Evidence Layer
        |                     |                     |
  BM25 + embeddings     Local classifiers      Provenance tracking
  RRF + reranker        Local NLP              Citation validation
  Filtering             Entity extraction      Source passages
  Caching               Similarity models      Confidence scoring
        |                     |                     |
        +---------------------+---------------------+
                              |
                      OPTIONAL AI GATEWAY
                              |
                Local LLM preferred / External API fallback
```

### Development Phases

#### Phase 0: Foundation Stabilization (Weeks 1-2)

**Objective:** Clean, document, and stabilize the current system before adding features.

**Tasks:**
1. Codebase cleanup
   - Remove all "FactCheckAI" branding, update to "TruvantaAI"
   - Clean old/stale API URLs and dead code
   - Remove duplicate implementations
   - Update all documentation

2. Extension refactoring
   - Split into logical modules: content/, background/, sidepanel/, popup/, shared/
   - Separate concerns: selection.js, toolbar.js, page-detector.js, highlighter.js
   - Implement proper message passing architecture
   - Create reusable API client and storage utilities

3. Backend documentation
   - Document complete fact-check pipeline (claim → verdict)
   - Map all data flows and dependencies
   - Document existing models and database tables
   - Create architecture diagrams

4. Performance baseline
   - Benchmark current latency across all endpoints
   - Measure cache hit rates
   - Profile database query performance
   - Establish success metrics

**Deliverables:**
- Clean, well-organized codebase with clear module boundaries
- Comprehensive technical documentation
- Performance baseline metrics for future comparison
- Stable foundation ready for new features

#### Phase 1: Shared Intelligence Layer (Weeks 3-4)

**Objective:** Build common infrastructure that both Verify and Research engines will use.

**Implementation Details:**

1. **Local Embeddings Service**
   - Replace external embedding APIs with sentence-transformers
   - Model: all-MiniLM-L6-v2 (22M parameters, 384 dimensions)
   - Content-based caching using SHA256 hashes
   - 7-day TTL for embedding cache
   - No external API calls for embeddings

2. **Local Reranking**
   - Implement cross-encoder reranking with ms-marco-MiniLM-L-6-v2
   - Replace LLM-based relevance scoring
   - Batch processing for efficiency
   - Fallback to BM25 scoring if model unavailable

3. **Unified Evidence Model**
   - Single Evidence class for both fact-check and research
   - Source type enum: WEB, NEWS, GOVERNMENT, ACADEMIC, JOURNAL, CONFERENCE, PREPRINT
   - Provenance tracking: SOURCE, COMPUTED, EXTRACTED, LOCAL_MODEL, LLM
   - Standardized metadata structure

4. **Enhanced Retrieval Pipeline**
   - Unified retrieval for both engines
   - Source-type filtering at query time
   - Improved RRF (Reciprocal Rank Fusion) implementation
   - Query-time boosting for academic sources when appropriate

5. **Smart Request Router**
   - Determines processing mode: verify_only, verify_plus_academic, research_deep
   - Routes based on page context (is academic paper?)
   - Optimizes resource usage by selecting minimal necessary pipeline

**Deliverables:**
- Local embeddings service (zero external API cost)
- Local reranking model (improved relevance without LLM)
- Unified Evidence model used across both engines
- Single retrieval pipeline with source-type awareness
- Intelligent request routing for performance optimization

#### Phase 2: Strengthen Fact-Check Core (Weeks 5-6)

**Objective:** Reduce external AI dependency in the core fact-checking pipeline.

**Implementation Details:**

1. **Deterministic Claim Detection**
   - SpaCy-based linguistic analysis
   - Pattern matching for factual assertions
   - Named entity recognition (NER)
   - Numerical and temporal claim detection
   - Question filtering (claims are not questions)
   - No LLM required

2. **Evidence-Based Verdict Engine**
   - Algorithmic verdict calculation from evidence
   - Support/contradiction score aggregation
   - Source diversity bonus (unique sources weighted higher)
   - Recency factor (newer evidence weighted more)
   - Verdict thresholds: SUPPORTED (≥0.7), LIKELY_SUPPORTED (≥0.4), MIXED (-0.4 to 0.4), LIKELY_FALSE (≤-0.4), FALSE (≤-0.7)
   - Confidence calculation independent of LLM
   - Returns INSUFFICIENT when evidence count below threshold

3. **Source Quality Scoring**
   - Domain reputation database (nature.com: 0.95, .gov: 0.90, .edu: 0.85)
   - Source type bonuses (JOURNAL +0.1, GOVERNMENT +0.1, ACADEMIC +0.08)
   - Publication recency factor
   - Citation count consideration for academic sources
   - Deterministic calculation, no AI required

4. **Evidence Stance Classification**
   - Local NLP model for stance detection
   - Categories: supporting, contradicting, neutral, tangential
   - Confidence scores per classification
   - Training on existing fact-check database
   - Fallback to lexical similarity if model unavailable

**Key Algorithm: Verdict Calculation**
```
net_score = (Σ support_scores - Σ contradict_scores) + diversity_bonus
confidence = net_score × recency_factor
verdict = threshold_mapping(net_score)
```

**Deliverables:**
- Local claim detection (replaces LLM extraction)
- Deterministic verdict engine (explicit logic, no black box)
- Source quality database and scoring system
- Evidence stance classifier (local model)
- Comprehensive test suite with benchmark dataset
- Target: 85%+ of verdicts determined without external AI

#### Phase 3: Research Detection & Metadata (Weeks 7-8)

**Objective:** Automatically detect and identify academic papers without AI.

**Implementation Details:**

1. **Paper Detection System**
   - HTML meta tag parsing (citation_doi, citation_title, citation_author)
   - DOI pattern matching: 10.XXXX/...
   - arXiv ID detection: arXiv:XXXX.XXXXX
   - PMID extraction: PMID: XXXXXXXX
   - Schema.org ScholarlyArticle detection
   - Academic domain recognition (arxiv.org, ieee.org, acm.org, nature.com, etc.)
   - Publisher identification
   - Zero AI dependency

2. **Paper Identity Resolution**
   - Priority hierarchy: DOI → PMID → arXiv → OpenAlex ID → Semantic Scholar ID → Title+Authors+Year
   - Canonical paper ID assignment (prevents duplicates)
   - Fuzzy title matching for papers without identifiers (Levenshtein distance)
   - Author name normalization
   - Cross-reference resolution across databases

3. **Academic Metadata Service**
   - OpenAlex integration (comprehensive, free API)
   - Crossref integration (DOI metadata)
   - Semantic Scholar integration (citation data)
   - Metadata normalization layer
   - Fields extracted: title, authors, year, venue, abstract, citations, references, topics, open access status
   - Aggressive caching (papers don't change often)

4. **Database Schema**
   - papers table (canonical_id, doi, pmid, arxiv_id, title, abstract, year, venue, citations_count)
   - paper_authors table (author names, positions, affiliations)
   - paper_identifiers table (all identifiers for cross-referencing)
   - paper_methods table (methods mentioned in paper)
   - paper_datasets table (datasets used in paper)
   - paper_metrics table (reported metrics and values)
   - paper_embeddings table (abstract and section embeddings)
   - paper_references, paper_citations tables (citation graph)

**Deliverables:**
- Multi-source paper detection (DOI, arXiv, PMID, metadata)
- Canonical paper identity system (no duplicates)
- Integration with three academic APIs (OpenAlex, Crossref, Semantic Scholar)
- Complete research database schema
- Automated metadata enrichment pipeline
- Paper detected notification in extension

#### Phase 4: Research Comparison Engine (Weeks 9-10)

**Objective:** Build the hero feature - comparing claims across papers.

**Hero Feature: Compare**

When a user highlights a claim like "RoBERTa achieved 93.2% accuracy on WELFake", TruvantaAI:
1. Extracts entities: method (RoBERTa), dataset (WELFake), metric (accuracy), value (93.2%)
2. Finds papers using the same method/dataset/metric combination
3. Extracts their reported results
4. Builds structured comparison table
5. Retrieves exact evidence passages from papers
6. Shows agreements, disagreements, and context

**Implementation Details:**

1. **Entity Extraction Pipeline**
   - Method detection: dictionary of ML/AI methods (BERT, RoBERTa, GPT, LSTM, CNN, Transformer, etc.)
   - Dataset detection: dictionary of research datasets (WELFake, LIAR, FakeNewsNet, ImageNet, COCO, etc.)
   - Metric detection: dictionary of evaluation metrics (accuracy, precision, recall, F1, AUC, BLEU, ROUGE, etc.)
   - Numerical value extraction: regex patterns for percentages, decimals
   - Context extraction: surrounding sentences for disambiguation
   - No LLM required for most academic entities

2. **Paper Retrieval for Comparison**
   - Query papers by method name (join through paper_methods table)
   - Query papers by dataset name (join through paper_datasets table)
   - Query papers by metric name (join through paper_metrics table)
   - Combined queries for method+dataset pairs
   - Ranking by relevance (exact match > partial match)
   - Limit to top 10 most relevant papers

3. **Comparison Table Builder**
   - Structured table: Paper | Method | Dataset | Metric | Value | Year | Citations | Open Access
   - Automatic value alignment (normalize percentages, decimals)
   - Highlight differences (values differing by >5% flagged)
   - Sort options: by year, by citations, by metric value
   - Export to CSV/JSON

4. **Evidence Passage Extraction**
   - Retrieve exact sentences mentioning the method+dataset+metric
   - Section identification (Abstract, Results, Discussion)
   - Page number extraction when available
   - Confidence score per passage
   - Direct links to paper sources

5. **Related Papers Engine**
   - Multi-signal relatedness scoring:
     - Semantic similarity (embeddings): 30%
     - BM25 lexical similarity: 20%
     - Citation relationship: 20%
     - Reference overlap: 15%
     - Method overlap: 10%
     - Dataset overlap: 10%
     - Author overlap: 10%
     - Topic similarity: 10%
     - Recency bonus: 5%
   - Weighted combination (tunable after evaluation)
   - No pure embedding similarity (adds academic graph context)

**Comparison Table Example:**
```
Claim: "RoBERTa achieved 93.2% accuracy on WELFake"

┌──────────────────────┬─────────┬─────────┬──────────┬───────┬──────┬──────────┐
│ Paper                │ Method  │ Dataset │ Accuracy │ Year  │ Cites│ Open     │
├──────────────────────┼─────────┼─────────┼──────────┼───────┼──────┼──────────┤
│ Current claim        │ RoBERTa │ WELFake │ 93.2%    │ -     │ -    │ -        │
│ Smith et al.         │ RoBERTa │ WELFake │ 91.4%    │ 2023  │ 45   │ Yes      │
│ Chen et al.          │ RoBERTa │ WELFake │ 94.1%    │ 2024  │ 12   │ Yes      │
│ Kumar et al.         │ BERT    │ WELFake │ 89.7%    │ 2023  │ 78   │ No       │
└──────────────────────┴─────────┴─────────┴──────────┴───────┴──────┴──────────┘

Evidence from Chen et al. (2024):
"Using RoBERTa-base fine-tuned on WELFake, we achieved 94.1% accuracy with 
cross-domain evaluation on FakeNewsNet..." [Results, p.7]

Evidence from Smith et al. (2023):
"RoBERTa obtained 91.4% accuracy on the WELFake test set, outperforming 
BERT by 2.3 percentage points..." [Abstract]
```

**Deliverables:**
- Entity extraction system (methods, datasets, metrics)
- Paper comparison engine with structured tables
- Related papers algorithm with academic graph signals
- Evidence passage extraction with provenance
- Comparison UI in side panel
- This is the MVP differentiator feature

#### Phase 5: Research Library & Citations (Weeks 11-12)

**Objective:** Allow researchers to save and organize findings.

**Implementation Details:**

1. **Collection Management**
   - User-created collections (e.g., "Fake News Detection Papers", "Transformer Research")
   - Collection metadata: name, description, created date, paper count
   - Multi-collection support (papers can be in multiple collections)
   - Collection sharing (future: export/import)

2. **Paper Saving**
   - One-click save from any detected paper
   - Automatic metadata capture
   - Manual tagging support
   - Notes per saved paper
   - Saved date tracking

3. **Highlight Management**
   - Save exact text selections with context
   - Automatic section detection
   - Page number capture
   - URL to exact location
   - Tags per highlight
   - Notes per highlight
   - Export highlights to markdown

4. **Literature Matrix Generator**
   - Automatic table generation from collection
   - Rows: papers, Columns: features (methods, datasets, metrics, evaluation types)
   - Cell values: checkmarks, actual values, or dashes
   - Aggregation statistics
   - Export to CSV, Excel, LaTeX
   - No AI required (pure data aggregation)

**Literature Matrix Example:**
```
Collection: Fake News Detection (20 papers)

┌─────────────────┬─────────┬──────────┬─────────┬─────────────┬───────────┬──────┐
│ Paper           │ RoBERTa │ WELFake  │ F1      │ Cross-dom   │ Ablation  │ Code │
├─────────────────┼─────────┼──────────┼─────────┼─────────────┼───────────┼──────┤
│ Paper A (2024)  │    ✓    │    ✓     │  93.2%  │      ✓      │     ✓     │  ✓   │
│ Paper B (2023)  │    ✓    │    ✓     │  91.4%  │      -      │     -     │  ✓   │
│ Paper C (2023)  │    -    │    ✓     │  89.7%  │      ✓      │     ✓     │  -   │
│ Paper D (2024)  │    ✓    │    -     │  94.8%  │      ✓      │     ✓     │  ✓   │
│ ...             │   ...   │   ...    │  ...    │     ...     │    ...    │ ...  │
├─────────────────┼─────────┼──────────┼─────────┼─────────────┼───────────┼──────┤
│ Total (n=20)    │  14/20  │  16/20   │  18/20  │    5/20     │   8/20    │12/20 │
│ Percentage      │   70%   │   80%    │   90%   │     25%     │    40%    │  60% │
└─────────────────┴─────────┴──────────┴─────────┴─────────────┴───────────┴──────┘
```

5. **Citation Generator**
   - Format support: APA 7, IEEE, MLA, Chicago, Harvard, BibTeX, RIS
   - Automatic formatting from structured metadata
   - Batch citation generation
   - Copy to clipboard
   - Export citation list
   - No AI required (template-based formatting)

**Deliverables:**
- Research library system (collections, saved papers, highlights, notes)
- Literature matrix generator with export options
- Pattern aggregation across collections
- Citation generator (multiple formats)
- Library UI in extension side panel

#### Phase 6: Pattern Detection & Research Gaps (Weeks 13-14)

**Objective:** Identify patterns and potential research gaps algorithmically.

**Implementation Details:**

1. **Pattern Detection Engine**
   - Method frequency analysis (most/least used methods)
   - Dataset usage patterns (popular vs underexplored datasets)
   - Metric coverage (which metrics are standard vs rare)
   - Evaluation practice analysis (cross-domain testing %, robustness evaluation %, ablation studies %)
   - Temporal trends (methods gaining/losing popularity)
   - All computed from structured data, no AI

2. **Missing Combination Finder**
   - Build matrix of all method×dataset combinations observed
   - Identify all possible combinations from available methods/datasets
   - Flag missing combinations (never tested together)
   - Rank by potential interest (based on individual popularity)
   - Example: "RoBERTa tested on WELFake 14 times, but never on FEVER"

3. **Contradiction Detection**
   - Group papers by method+dataset combination
   - Compare reported metric values within each group
   - Flag high variance (>10% difference for same setup)
   - Identify potential contradictions requiring investigation
   - Provide paper IDs for manual review

4. **Evaluation Gap Analysis**
   - Calculate % of papers performing cross-domain evaluation
   - Calculate % of papers performing robustness testing
   - Calculate % of papers performing ablation studies
   - Calculate % of papers performing human evaluation
   - Identify underused evaluation practices

5. **Research Gap Generator**
   - Generate gap descriptions from computed patterns
   - Format: "Observed: X/Y papers use Z. Potential gap: ..."
   - Always label as "potential" or "observed underexplored area"
   - Never claim definitive gaps (requires human judgment)
   - Include evidence backing (paper IDs)
   - Provenance: COMPUTED (from data) vs LLM (interpretation)

**Pattern Detection Example:**
```
Collection: Fake News Detection (20 papers analyzed)

Method Trends:
  RoBERTa:      14/20 (70%)  [Most common]
  BERT:         10/20 (50%)
  LSTM:          4/20 (20%)
  CNN:           3/20 (15%)  [Underused]

Dataset Usage:
  WELFake:      16/20 (80%)  [Most common]
  LIAR:          8/20 (40%)
  FakeNewsNet:   6/20 (30%)
  FEVER:         2/20 (10%)  [Underused]

Evaluation Coverage:
  Accuracy:           20/20 (100%)  [Universal]
  F1 Score:           18/20 (90%)
  Cross-domain test:   5/20 (25%)   [Underused]
  Robustness test:     3/20 (15%)   [Underused]
  Ablation study:      8/20 (40%)
  Human evaluation:    2/20 (10%)   [Rare]

Potential Research Gaps:
1. Cross-domain robustness evaluation (only 5/20 papers)
   Evidence: Papers #3, #7, #12, #14, #18
   
2. RoBERTa on FEVER dataset (14 papers use RoBERTa, 2 use FEVER, 0 use both)
   Missing combination opportunity
   
3. Human evaluation remains rare (2/20 papers)
   Evidence: Papers #9, #16
```

**Optional AI Enhancement:**
- After computing patterns, optionally use local/external LLM to improve wording
- LLM receives structured data, not raw papers
- LLM generates interpretive text, not conclusions
- Original computed data always included
- Provenance clearly marked: COMPUTED (data) + LLM (interpretation)

**Deliverables:**
- Pattern detection engine (methods, datasets, metrics, evaluation practices)
- Missing combination finder
- Contradiction detector
- Evaluation gap analyzer
- Research gap generator (data-driven)
- Optional LLM enhancement for natural language generation

#### Phase 7: AI Gateway & Controlled Synthesis (Weeks 15-16)

**Objective:** Add optional AI layer for interpretation and synthesis only.

**Implementation Details:**

1. **AI Gateway Architecture**
   - Central routing point for all AI requests
   - Provider enum: LOCAL, GEMINI, OPENAI, CLAUDE
   - Decision tree: deterministic → local model → external API
   - Provider selection based on task type and config
   - Aggressive response caching (content-based)
   - Usage tracking and cost monitoring

2. **Local LLM Integration**
   - Optional local model support (e.g., Llama, Phi, Mistral)
   - Configurable model path and parameters
   - Automatic fallback to external if local unavailable
   - Quantization support for resource-constrained environments
   - Batch processing for efficiency

3. **External Provider Management**
   - Multi-provider support (Gemini, OpenAI, Claude, Groq, Cerebras)
   - Automatic failover on error
   - Rate limit handling
   - Cost tracking per provider
   - Provider selection based on task (reasoning vs generation)

4. **Controlled Literature Synthesis**
   - Synthesis only after structured data collected
   - Input: aggregated methods, datasets, findings (not raw papers)
   - Output: interpretive text with evidence references
   - Citation extraction and validation
   - Provenance: LLM clearly labeled
   - Example tasks: "Synthesize findings from 12 papers", "Explain contradiction between Paper A and Paper B"

5. **AI Usage Policies**
   - Paper detection: NO AI
   - Metadata extraction: NO AI
   - Citation generation: NO AI
   - Retrieval/ranking: NO AI (local models only)
   - Verdict calculation: NO AI (deterministic)
   - Related papers: NO AI (algorithmic)
   - Pattern detection: NO AI (computational)
   - Ambiguous interpretation: LOCAL AI FIRST
   - Synthesis/explanation: LOCAL AI FIRST, external fallback
   - Complex writing: EXTERNAL AI ALLOWED

6. **AI Usage Tracking**
   - Log every AI request (task type, provider, tokens, latency, cached)
   - Daily/weekly usage reports
   - Cost estimation per provider
   - Cache hit rate monitoring
   - Target: 90-95% of requests complete without external AI

**AI Gateway Flow:**
```
Feature request arrives
    ↓
Is deterministic solution available?
    YES → Use deterministic code → RETURN
    NO ↓
    ↓
Is local model available?
    YES → Use local model → SUCCESS? → RETURN
    NO ↓                         FAIL ↓
    ↓                                 ↓
External AI (fallback) ←──────────────┘
    ↓
Cache result
    ↓
RETURN (with provenance label)
```

**Deliverables:**
- AI Gateway with local-first fallback logic
- Local LLM integration (optional)
- Multi-provider external API support
- Controlled literature synthesis
- Evidence-backed AI responses
- Comprehensive usage tracking and cost monitoring
- Clear provenance labeling (COMPUTED vs LOCAL_MODEL vs LLM)

### Extension User Experience Updates

#### New Selection Toolbar
```
┌──────────────────────────────────────────────┐
│ Verify │ Compare │ Find Papers │ Save │ Cite │
└──────────────────────────────────────────────┘
```

**Contextual Display:**
- Normal web page: Show only [Verify] [Save]
- Academic paper: Show all actions
- User preference: Can hide/show actions

**Action Descriptions:**
- Verify: Original fact-check (always available)
- Compare: Compare claim across papers (academic context only)
- Find Papers: Search academic literature for related papers
- Save: Save highlight to research library
- Cite: Generate citation for current paper (paper context only)

#### Enhanced Side Panel

**Three Main Tabs:**

1. **Verify Tab** (Default for non-academic pages)
   - Claim display
   - Verdict with confidence
   - Evidence list with sources
   - Explanation text
   - Manipulation analysis (if applicable)

2. **Research Tab** (Auto-appears on academic pages)
   - Paper information (title, authors, year, venue, DOI)
   - Paper metadata (citations, open access, topics)
   - Comparison section (when Compare is clicked)
   - Related papers list (ranked by relevance)
   - Citation graph visualization (future)

3. **Library Tab**
   - Collections list
   - Saved papers per collection
   - Highlights list (with filters)
   - Notes list
   - Export options

#### Page Detection Indicator

**When academic paper detected:**
```
┌─────────────────────────────────────┐
│ RESEARCH PAPER DETECTED             │
│                                     │
│ Attention Is All You Need           │
│ Vaswani et al. • 2017 • NeurIPS    │
│                                     │
│ DOI: 10.xxx/xxx ✓  Open Access ✓   │
│                                     │
│ [Analyze Paper]  [Save]  [Cite]    │
└─────────────────────────────────────┘
```

### Implementation Timeline

**16-Week Roadmap**

| Week | Phase | Main Deliverables |
|------|-------|-------------------|
| 1-2 | Phase 0 | Clean codebase, documentation, baseline metrics |
| 3-4 | Phase 1 | Local embeddings, unified retrieval, request router |
| 5-6 | Phase 2 | Deterministic verdict engine, local claim detection |
| 7-8 | Phase 3 | Paper detection, identity resolution, metadata service |
| 9-10 | Phase 4 | **Comparison engine (MVP milestone)**, related papers |
| 11-12 | Phase 5 | Research library, literature matrix, citations |
| 13-14 | Phase 6 | Pattern detection, research gaps |
| 15-16 | Phase 7 | AI gateway, controlled synthesis |

**Key Milestones:**
- Week 2: Stable foundation
- Week 4: Local-first infrastructure complete
- Week 6: Enhanced fact-check core
- Week 8: Research detection working
- Week 10: **Compare feature demo-ready (public beta)**
- Week 12: Full research library
- Week 14: Pattern analysis complete
- Week 16: Production-ready with optional AI

### Success Metrics

**Product Usage Metrics**
- Daily active users (DAU)
- Verify requests per day (baseline: existing traffic)
- Compare requests per day (new feature)
- Papers saved per user (new feature)
- Highlights created per user (new feature)
- Collections created per user (new feature)

**Quality Metrics**
- Verdict accuracy vs benchmark dataset (target: maintain ≥90%)
- Paper detection accuracy (target: ≥95% for papers with DOI)
- Comparison relevance (manual evaluation, target: ≥80% relevant papers)
- User satisfaction rating (target: ≥4.2/5.0)

**Performance Metrics**
- Verify latency P50/P95 (target: <2s / <5s)
- Compare latency P50/P95 (target: <3s / <7s)
- Paper detection latency (target: <500ms)
- Cache hit rate (target: ≥70%)
- External AI dependency (target: ≤10% of requests)

**Cost Metrics**
- API cost per 1000 requests (target: <$0.50)
- Database storage cost per user (target: <$0.10/month)
- Total monthly infrastructure cost (target: <$100 for 10k users)

### Risk Mitigation

**Technical Risks**

1. **Risk:** Local models not accurate enough
   - Mitigation: Benchmark early, maintain external AI fallback, iterative model improvement
   - Contingency: Gradually transition, keep external AI as default during testing

2. **Risk:** Academic API rate limiting
   - Mitigation: Aggressive caching (papers rarely change), request throttling, multiple API sources
   - Contingency: Implement exponential backoff, queue non-urgent requests

3. **Risk:** Performance degradation with research features
   - Mitigation: Progressive loading, lazy evaluation, database indexing, CDN for static content
   - Contingency: Feature flags to disable research mode if performance issues

4. **Risk:** Extension store policy violations
   - Mitigation: Clear permission explanations, privacy policy update, gradual rollout
   - Contingency: Separate research features into optional module

**Product Risks**

1. **Risk:** Users confused by research features
   - Mitigation: Contextual display (hide on non-academic pages), onboarding flow, tooltips
   - Contingency: Add "Research Mode" toggle in settings

2. **Risk:** Feature creep slows development
   - Mitigation: Strict phase discipline, MVP focus (Compare feature first), defer non-critical features
   - Contingency: Push non-essential features to post-launch roadmap

3. **Risk:** Accuracy concerns hurt user trust
   - Mitigation: Clear provenance labels, confidence scores, limitations disclosure, "potential" language for gaps
   - Contingency: Add disclaimers, provide feedback mechanism

4. **Risk:** Academic users expect features we don't have
   - Mitigation: Clear positioning ("research verification" not "reference manager"), compare against specific competitors
   - Contingency: Partner with existing tools (Zotero integration) rather than compete

### Competitive Positioning

**TruvantaAI vs Existing Tools**

| Product | Core Function | TruvantaAI Advantage |
|---------|---------------|----------------------|
| Zotero | Reference management | In-page comparison, claim verification |
| Semantic Scholar | Paper search & discovery | Browser integration, claim-level comparison |
| ResearchRabbit | Literature mapping | Real-time verification, evidence extraction |
| Scite | Citation context | Fact-checking + academic analysis combined |
| Connected Papers | Visual paper exploration | Quantitative comparison tables |
| Elicit | AI research assistant | Evidence-backed, local-first, transparent provenance |

**Unique Value Proposition:**
"TruvantaAI helps researchers verify claims and instantly see how they compare across academic literature, with exact evidence passages and transparent provenance - all from within the browser."

**Target Users:**
1. Academic researchers writing literature reviews
2. Graduate students conducting literature surveys
3. Fact-checkers needing academic evidence
4. Science journalists verifying claims
5. Peer reviewers checking cited claims

### Technical Debt & Cleanup Items

**Before Phase 0:**
- Audit all external API dependencies
- Document current database schema completely
- Identify deprecated code paths
- List all TODOs and FIXMEs
- Review security vulnerabilities

**During Phase 0:**
- Migrate from FactCheckAI to TruvantaAI branding everywhere
- Consolidate duplicate retrieval code
- Standardize error handling patterns
- Implement consistent logging
- Update all dependencies to latest stable versions

**Ongoing:**
- Weekly code review sessions
- Monthly dependency updates
- Quarterly security audits
- Performance profiling per phase

### Future Vision (Beyond 16 Weeks)

**Phase 8: Advanced Features (Weeks 17-20)**
- Firefox and Edge extension support
- Multilingual paper support (detect language, translate metadata)
- PDF annotation integration
- Export literature review drafts
- Collaborative collections (team research)

**Phase 9: Enterprise Features (Weeks 21-24)**
- Self-hosted deployment option
- Custom paper corpus integration
- API for institutional access
- Bulk analysis tools
- Usage analytics dashboard

**Phase 10: AI-Powered Enhancements (Weeks 25-28)**
- Research question generation from gaps
- Automated literature review drafting
- Hypothesis suggestion based on patterns
- Experimental design recommendations
- Always optional, always evidence-backed

### Getting Started with New Plan

**Immediate Next Steps:**

1. **Review & Approve**
   - Stakeholder review of this plan
   - Confirm resource availability
   - Adjust timeline if needed
   - Sign-off on Phase 0 start

2. **Set Up Project Tracking**
   - Create GitHub Projects board or Jira workspace
   - Define sprint structure (2-week sprints)
   - Create issues for Phase 0 tasks
   - Set up daily standup schedule

3. **Prepare Development Environment**
   - Document current local setup
   - Create development database snapshot
   - Set up staging environment
   - Prepare test data sets

4. **Create Benchmarking Dataset**
   - Collect 100 diverse claims (50 real, 50 fake)
   - Document expected verdicts
   - Establish baseline accuracy
   - Use for regression testing throughout phases

5. **Begin Phase 0 Execution**
   - Week 1: Codebase cleanup and branding update
   - Week 2: Documentation and baseline metrics
   - End of Week 2: Go/No-Go decision for Phase 1

**Communication Plan:**
- Weekly progress updates (Friday EOD)
- Bi-weekly phase reviews (every other Monday)
- Monthly stakeholder demos
- Slack channel for daily coordination
- GitHub Issues for technical discussions

---

##  Deployment (100% Free, No Credit Card)

**Complete deployment guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

### Quick Deploy (5 minutes)

1. **Database:** [neon.tech](https://neon.tech) → Create project → Copy connection URL
2. **ML Models:** [huggingface.co/spaces](https://huggingface.co/spaces) → Create Space → Upload `ml-servers/huggingface-ensemble/`
3. **Backend:** [render.com](https://render.com) → Blueprint → Connect repo → Set env vars
4. **Keep Awake:** [uptimerobot.com](https://uptimerobot.com) → Add monitors (ping every 5 min)

**Architecture:**
```
Chrome Extension → Render (FastAPI) → Neon (PostgreSQL+pgvector) + HF Spaces (RoBERTa)
                       ↑
                UptimeRobot keeps alive
```

**Cost:** $0/month forever

**See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for step-by-step instructions.**

---

## Installation & Setup

### Quick Start (5 minutes)

See [QUICK_START.md](QUICK_START.md) for the fastest way to deploy (100% free, no credit card).

### Full Deployment Guide

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete step-by-step instructions.

### Keep Services Awake

See [KEEP_ALIVE_SETUP.md](KEEP_ALIVE_SETUP.md) to configure monitoring and prevent cold starts.

### Chrome Extension

**Option 1: Install from Chrome Web Store** (Recommended)  
[Install FactCheckAI](https://chromewebstore.google.com/detail/factcheckai) - One-click install

**Option 2: Manual Install (Developers)**

```bash
git clone https://github.com/BharatChandra-sys/TruvantaAI.git
cd FactCheckAI

# Chrome -> Extensions -> Developer mode -> Load unpacked -> select 'extension' folder
# Update extension/config.js with your backend URL
```

### Backend (Local Development)

```bash
cd backend
py -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

cp .env.example .env
# Fill in keys

uvicorn app.main:app --reload --port 8000
```

Required `.env` keys:
```
DATABASE_URL=postgresql://...neon.tech/neondb?sslmode=require
JWT_SECRET=<openssl rand -hex 32>
GOOGLE_CLIENT_ID=...
GROQ_API_KEY=...
TAVILY_API_KEY=...
BREVO_API_KEY=...
SMTP_USER=...
```

### Deploy to Render + Neon

1. Create a Neon project at neon.tech — copy the pooled connection string
2. Connect repo to Render → New → Blueprint → render.yaml handles everything
3. Set `DATABASE_URL` and API keys in Render's environment tab
4. Deploy — startup sequence runs DB connection check, creates tables, applies migrations

---

## API Reference

### Authentication

```bash
curl -X POST https://factcheckai-backend.onrender.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass","name":"Your Name"}'

# Returns {"token": "eyJ...", "user": {...}}
# Use in: Authorization: Bearer <token>
```

### Fact-Check

```bash
curl -X POST https://factcheckai-backend.onrender.com/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"5G towers spread coronavirus through radio waves"}'
```

```json
{
  "is_claim": true,
  "verdict": "fake",
  "confidence": 0.87,
  "ml_score": 0.81,
  "ai_score": 0.85,
  "evidence_score": 0.22,
  "manipulation_score": 0.63,
  "explanation": "...",
  "evidence": ["https://...", "https://..."],
  "highlights": [{"phrase": "5G towers", "importance": 0.9}]
}
```

### Health Check

```bash
curl https://factcheckai-backend.onrender.com/health
```

### Rate Limits

| Tier | Per minute | Per day | Monthly |
|------|-----------|---------|---------|
| Anonymous | 3 | 10 | 10 |
| Free | 5 | 30 | 30 |
| Pro | 60 | 10,000 | 1,000 |
| Enterprise | 300 | 100,000 | unlimited |

---

## Development & Contributing

1. Fork and create a feature branch from `main`
2. Follow PEP 8, use type hints throughout
3. Use conventional commits: `feat:`, `fix:`, `docs:`
4. Open a pull request with a clear description

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## Security & Compliance

- **JWT** — HS256, 7-day expiry, stateless
- **Google OAuth** — access token validated with audience claim check
- **Rate limiting** — per-IP sliding window in middleware; per-user tier limits via Redis
- **Input validation** — Pydantic validators, HTML stripping, null-byte removal
- **Parameterized queries** — SQLAlchemy ORM throughout; no raw SQL with user input
- **GDPR-aware** — no PII stored beyond what users explicitly provide
- **Open source** — all logic is auditable

---

## Roadmap

### Near-term
- [x] fine-tuned RoBERTa model-b uploaded to `Bharat2004/factcheckai-model-b`
- [x] HuggingFace Space ensemble server built (`ml-servers/huggingface-ensemble/`)
- [x] pgvector persistent memory schema + Alembic migration deployed to Neon
- [x] Hybrid retrieval (BM25 + vector + RRF + cross-encoder reranker)
- [x] LangGraph workflow orchestration (9 nodes, conditional edges)
- [x] RAG reasoner + citation validator
- [x] Agent tool definitions (search_news, retrieve_evidence, run_ml_analysis, etc.)
- [ ] Upload model-a after training completes; set `ML_SERVER_1_URL` in Render
- [ ] Deploy HF Space; set `ML_SERVER_2_URL` in Render

### Medium-term
- [ ] Evaluation ablation study (TF-IDF vs hybrid vs hybrid+RAG vs full)
- [ ] Firefox extension support
- [ ] Multilingual expansion (German, Portuguese, French)

### Long-term
- [ ] Separate background scheduler service (Celery or cron)
- [ ] LangSmith observability traces (per-node latency and token cost)
- [ ] Streaming response for long documents

---

## License & Attribution

```
FactCheckAI: Apache License 2.0
├── FastAPI: MIT
├── LangChain / LangGraph: MIT
├── Transformers (HuggingFace): Apache 2.0
├── scikit-learn: BSD 3-Clause
├── pgvector: MIT
└── PostgreSQL: PostgreSQL License
```

Training data:
- LIAR dataset — Wang, 2017
- ISOT Fake News Dataset
- FakeNewsNet — Shu et al., 2018
- daniB2112/fake-news-dataset (HuggingFace)
- WELFake, GonzaloA/fake_news, FEVER v1.0

```bibtex
@software{factcheckai2027,
  title   = {FactCheckAI: Memory-Augmented Agentic Fact Verification},
  author  = {Bodapati Bharat Chandra},
  year    = {2027},
  url     = {https://github.com/BharatChandra-sys/TruvantaAI},
  version = {2.7.0},
  license = {Apache-2.0}
}
```

---

<p align="center">
  <br/>
  <b>Open-source fact-checking — owned ML, persistent memory, agentic RAG</b>
  <br/><br/>
  <a href="https://github.com/BharatChandra-sys/TruvantaAI/stargazers">
    <img src="https://img.shields.io/github/stars/BharatChandra-sys/TruvantaAI?style=for-the-badge&logo=github&color=4F46E5&labelColor=1e1e2e" alt="Stars"/>
  </a>
  <br/><br/>
  <a href="https://github.com/BharatChandra-sys/TruvantaAI/issues">Report Issues</a> •
  <a href="CONTRIBUTING.md">Contributing</a> •
  <a href="https://factcheckai-backend.onrender.com/health">Live API</a>
</p>
