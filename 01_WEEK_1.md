# Week 1: Calibration + First Real Concept

**Week of:** 2026-06-30
**Total time budget:** ~8 hours
**Goal:** Establish baseline, set up portfolio, and learn one foundational concept that pays off all year.

---

## Day-by-day (suggested, not rigid)

### Day 1-2 (2 hrs): Baseline Self-Assessment

Answer these honestly — bring the answers to our next session so I can calibrate the depth of teaching.

**Distributed Systems & Spark (rate 1-5):**
1. Can you explain *why* a Spark stage triggers a shuffle? What causes data skew and how do you fix it without `repartition`?
2. What is AQE (Adaptive Query Execution) and what 3 things does it actually do at runtime?
3. Difference between bucketing and partitioning in Spark/Hive? When would you choose each?
4. Walk through what happens when you run `df.write.format("delta").mode("append").save(...)` — what files get written, what metadata changes?

**SQL (rate 1-5):**
1. Write a query to find the 2nd highest salary per department, including ties. No `LIMIT`.
2. Given a table of user events (`user_id, event_time, event_type`), find users who did action A within 5 minutes of action B. (Sessionization pattern.)
3. Explain the difference between `RANGE` and `ROWS` in window functions.

**System Design (rate 1-5):**
1. Sketch the architecture for a real-time dashboard showing "orders per minute" across 1000 stores. What are your storage layers? Why?
2. What's the difference between Lambda and Kappa architecture? When do you still pick Lambda in 2026?

**AI / LLM (rate 1-5):**
1. Why does a RAG pipeline need *both* an embedding model and a chunking strategy? What goes wrong if chunks are too big? Too small?
2. What does "hallucination" actually mean technically? How would you measure it on your own RAG system?

For each: write down your honest rating (1 = "no idea", 5 = "I could teach this to a junior"). **Send me the ratings**, not detailed answers — I'll then know exactly where to push.

---

### Day 3 (1.5 hrs): Set Up Your Portfolio Repo

Create a GitHub repo: `data-platform-portfolio` (or your preferred name — public).

Structure:
```
data-platform-portfolio/
├── README.md           # Will become your portfolio landing page
├── 01-rag-pipeline/    # Phase 1 capstone — empty for now
├── 02-streaming/       # Phase 2 capstone — empty for now
├── learning-notes/     # Where you'll write up what you learn each week
└── interview-prep/     # SQL solutions, system design write-ups
```

**Why this matters (Staff-engineer perspective):** Hiring managers at top companies *will* look at your GitHub. A clean, well-organized portfolio with a couple of substantive projects beats 20 toy projects. We're building toward two anchor projects, not a graveyard.

**Common mistake:** People wait until they're "ready" to start the portfolio. Wrong. Start ugly, refine over time. Your README at month 6 will be 10x better than month 1 — that's evidence of growth.

---

### Day 4-6 (3.5 hrs): The First Real Concept — Embeddings

This is your entry into AI for Data Engineers. Embeddings are the single most important AI primitive a DE needs to understand because:
- Every RAG system depends on them
- Vector search is "the new index"
- They show up in real interview questions for senior DEs in 2026

**What I want you to learn:**

1. **The mental model (30 min):** An embedding is a deterministic function that maps text → high-dimensional vector such that semantically similar text → nearby vectors (by cosine similarity). That's it. Read OpenAI's docs on `text-embedding-3-small`. Look at the vector dimensions (1536 by default, can be reduced via Matryoshka).

2. **Why semantically nearby? (30 min):** Read about the geometric intuition — Sebastian Raschka's blog or Jay Alammar's "The Illustrated Word2Vec" — even though embeddings have moved past Word2Vec, the intuition transfers.

3. **Hands-on (2 hrs):**
   - Install: `pip install openai numpy scikit-learn`
   - Pick 20 sentences from your work domain (e.g., 10 about "data pipeline failures", 10 about "customer churn").
   - Embed all 20 using OpenAI's `text-embedding-3-small`.
   - Compute pairwise cosine similarity matrix.
   - Verify: do the "failure" sentences cluster together?
   - **Now the interesting part:** what happens if you embed a query like `"Why did the ETL job error last night?"` — does it correctly retrieve the failure cluster?
   - Save this as `learning-notes/week-01-embeddings.md` in your portfolio with your findings.

4. **The DE-specific angle (30 min):** Read about *embedding drift* and *re-embedding strategies* — what happens when OpenAI deprecates a model? How do you migrate a 100M-row vector store? This is the part most AI tutorials skip but a DE *must* know.

---

### Day 7 (2 hrs): System Design Seed + Reflection

**Update based on your baseline (SD=1/5):** I'm pulling System Design into Week 1 instead of waiting until Month 4. You need *reps*, and reps start now — badly is fine, just start.

#### System Design Exercise (1.5 hrs)

**The problem:**
> "Design a system that lets engineers at your company search across 5 years of Slack messages, GitHub PRs, and Notion docs using natural language. Pitch it to the VP of Engineering."

**Don't research how others did this.** I want to see *your* current thinking — what you draw on a whiteboard today. We'll compare it next week to a canonical design and that gap will teach you more than reading 10 blog posts.

**Constraints to think through:**
- ~100M messages, ~500K PRs, ~50K docs
- 500 engineers, all searching at once at peak
- New content arrives continuously
- Some content is sensitive (internal channels) — search must respect access controls

**Deliverable:** A markdown doc at `learning-notes/week-01-system-design.md` in your portfolio with these sections (try to spend ~15 min per section):

1. **Clarifying questions** — What would you ask the VP before designing? (List 8-10.)
2. **Scale estimation** — Rough numbers: storage size, queries/sec, embedding count, index size.
3. **High-level architecture** — A diagram (text/ASCII is fine) of components and data flow.
4. **Data ingestion** — How does new content get into the system? Batch? Stream? CDC?
5. **The retrieval layer** — How does a search query actually return results?
6. **Three biggest risks** — What scares you about this design?
7. **What you don't know** — Be honest. List 3-5 things you'd need to research before building.

**Don't aim for "right."** Aim for "I thought hard about trade-offs." Section 7 is the most important one for our learning — it tells me exactly where to teach next.

**Common rookie mistake at 1/5:** Jumping straight to "use Elasticsearch and OpenAI." That's a tool list, not a design. Force yourself to talk about the data first (volume, velocity, variety), then the access patterns, *then* the tools.

#### Reflection (30 min)

**Write a short reflection (~300 words) in `learning-notes/week-01-reflection.md`:**
- What surprised you about embeddings?
- What's still fuzzy?
- What did the system design exercise feel like? (Frustrating? Energizing? Paralyzing? All useful data.)
- One question you want me to answer next week

---

## What Success Looks Like at End of Week 1

- [x] Self-assessment ratings shared (done — Spark 3, SQL 4, SD 1, AI 1)
- [ ] Portfolio repo exists on GitHub (even if mostly empty)
- [ ] You can explain to a friend in 2 minutes: "what is an embedding and why do DEs care"
- [ ] You ran cosine similarity code yourself (not just read about it)
- [ ] You wrote a *bad* first system design doc (the goal is reps, not perfection)
- [ ] You wrote a reflection that's honest about what's still fuzzy

---

## When to Stop Reading and Start Doing

If you finish the embeddings hands-on in 90 minutes instead of 2 hours, **don't read more theory**. Spend the extra time on a stretch goal:

**Stretch goal:** Build a tiny RAG over your own notes/docs. Embed → store in numpy array → at query time, find top-3 chunks → send to Claude/GPT with the chunks as context → see what the answer looks like with vs. without retrieval.

This is your Phase 1 capstone in seed form.

---

## Career Growth Tip (this week)

Start a `WINS.md` file in your portfolio (or private). Each week, write 2-3 lines: "What did I learn that I didn't know last week?" This becomes the source material for your resume bullets, your interview stories, and your performance review. Senior engineers who get promoted track their own wins; everyone else hopes their manager remembers.
