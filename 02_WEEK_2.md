# Week 2: System Design Primary + Vector DB Hands-on

**Total time budget:** ~6-8 hours
**Goal:** Build the System Design muscle with a second full case study, level up from in-memory FAISS to a real vector DB, and answer the open question from Week 1.

**Pacing note:** progress is tracked by *completion of items*, not by calendar dates. Some items may take 30 min, some may take a full weekend — that's fine.

---

## Track Allocation

```
~7 hrs breakdown:
  ┌──────────────────────────────────────────┐
  │ System Design           ~4.0 hrs          │  ← primary
  │ AI / Vector DB          ~2.0 hrs          │  ← level up from FAISS
  │ SQL maintenance         ~1.0 hr           │  ← keep the 4/5 sharp
  └──────────────────────────────────────────┘
```

If short on time, drop SQL first, then Vector DB. Never drop SD.

---

## Track A — System Design (Primary, ~4 hrs)

### A1. Warm-up: Word2Vec question (~30 min)

**Question carried over from Week 1 reflection:**
> "If Word2Vec is obsolete, what are today's leading embedding approaches, and why does the Word2Vec intuition still hold?"

**Deliverable:** written up as `learning-notes/week-02-modern-embeddings.md` — what changed (architecture, contextualization, scale), what stayed the same (distributional hypothesis, geometric intuition), and what this means for a DE reasoning about embeddings in 2026.

### A2. Case Study #1 — Full SD design (~2.5 hrs)

**Prompt (pick one):**

**Option A — Design a real-time metrics platform** (like Datadog or Prometheus lite)
- Scale: 100M events/day, 100k custom metrics, 5k dashboards
- Latency: P99 query < 500ms for dashboards
- Freshness: metric visible within 30s of emission
- Retention: raw 30 days, aggregates 5 years

**Option B — Design a RAG platform** (ties Week 1 AI work to SD)
- Scale: 10M enterprise documents, 5k QPS, sub-second responses
- Access controls per document
- Model versioning + drift handling
- Serves an LLM-generated answer, not just retrieval

**Option C — Interview curveball — Design a feature store**
- Serves online (single-row, low-latency) and offline (batch training) reads
- 10k features, 100M entities, both real-time and batch-updated
- Consistency between online and offline is critical

**Deliverable:** full 7-section design doc at `system-designs/01_<name>.md`.

**Target this time:** all 7 sections. No skipping. Even short attempts on the hard sections count. Sections 5-7 are where the Week 1 gap lives — this exercise closes it.

Follow the framework in `system-designs/00_framework.md` — refer back to it during the exercise, not from memory.

### A3. DDIA Chapter 1 skim (~1 hr)

**Book:** *Designing Data-Intensive Applications* by Martin Kleppmann.
**Chapter:** 1 — *Reliable, Scalable, and Maintainable Applications*.
**Read for vocabulary, not depth.** Focus on:
- The 3 concerns (reliability, scalability, maintainability) as separable design axes
- Throughput vs. latency vs. response time — the distinction matters
- Load parameters — what "load" means depends on the system

**Deliverable:** 5-10 bullet notes in `learning-notes/ddia-chapter-01.md`. Not a summary — just the concepts you want to reuse in future SD conversations.

---

## Track B — AI / Vector DB (~2 hrs)

### B1. Stand up a real vector DB (~1.5 hrs)

Lab 01 used in-memory FAISS — fine for teaching, not production. Level up to a managed vector DB running locally.

**Pick one:**
- **Qdrant** (recommended — Rust, self-hosted, fast, popular)
- **Weaviate** (Python-friendly, more features)
- **pgvector** (PostgreSQL extension — closest to what most companies actually deploy)

**Tasks:**
1. Install locally (Docker recommended)
2. Load Lab 01 corpus + embeddings into it
3. Run the same 15 eval queries — verify recall@k matches your FAISS numbers
4. Add a filter: query only docs where `topic = "sql"` — this is the *feature FAISS didn't have*

**Deliverable:** new lab folder `labs/02-vector-db/` with README explaining what's different from Lab 01 and why the metadata filtering matters for real RAG.

### B2. Note: what's different in production (~30 min)

Read the vector DB's docs on:
- **Consistency model** — is a write visible immediately? Eventually?
- **Replication** — how does the DB survive a node loss?
- **Sharding** — at what point do you need it?

**Deliverable:** short notes in the Lab 02 README on how these three properties would show up in an interview answer.

---

## Track C — SQL Maintenance (~1 hr)

**Goal:** keep the 4/5 rating sharp. Do 2-3 hard problems.

**Suggested problems:**
1. Sessionization — given `(user_id, event_time, event_type)`, group into sessions where gap > 30 min
2. Top-K per group with ties — 3rd highest salary per department, including ties, no LIMIT
3. Rolling window over unevenly-spaced events — 7-day rolling active user count

**Sources:** DataLemur, StrataScratch, or LeetCode Database section.

**Deliverable:** none required. Just do the problems. If any felt hard, jot the pattern in `learning-notes/sql-patterns.md`.

---

## Success Criteria at End of Week 2

- [ ] `learning-notes/week-02-modern-embeddings.md` — Word2Vec question answered
- [ ] `system-designs/01_<name>.md` — full 7-section design doc (all sections attempted)
- [ ] `learning-notes/ddia-chapter-01.md` — vocabulary bullets from DDIA
- [ ] `labs/02-vector-db/` — Qdrant/Weaviate/pgvector running locally, Lab 01 corpus loaded, metadata filtering working
- [ ] SD self-rating updated (target: 1.5/5 → 2/5)

---

## What Success Looks Like Beyond The Checklist

- You've done **two SD case studies now**. Pattern recognition begins around case 4-5. You're on track.
- Your portfolio repo has **three distinct kinds of artifacts**: hands-on labs, learning notes, system design docs. That's stronger than 20 more Jupyter notebooks.
- You can articulate a **10-second answer** to *"how does semantic search work at scale?"* — because you've now built both the FAISS version and the real-DB version.

---

## Common Traps To Avoid In Week 2

1. **Skipping SD sections again.** The Week 1 exercise stopped at Section 4. Week 2 target: finish all 7, however roughly. Section 6-7 (risks + what you don't know) are shorter and easier than they look.
2. **Spending too long on Vector DB setup.** If the Docker install is fighting you for more than 30 min, pause and ask for help. Time for learning, not for wrangling infrastructure.
3. **Reading DDIA cover to cover.** Skim Chapter 1 for concepts. Do not read Chapters 2+ this week — you'll fatigue and never finish. Chapter 2 comes in Week 3.
4. **Doing SD passively.** Reading a design doc ≠ writing one. Force yourself to *write*, even badly.

---

## Career Growth Tip (this week)

**Time the SD case study.** Set a 45-minute timer for the design and see how far you get. Don't finish? That's the data — you'll know exactly which sections steal your time. Timing under pressure is a skill you build only through timed practice, and interviewers can tell instantly whether a candidate has practiced timed or untimed.

Real interview timings from candidates I've seen:
- Weak candidate spends 25 min on requirements + capacity, then panics on architecture
- Strong candidate spends 10 min on requirements + capacity, 30 min on deep dive + trade-offs

That distribution is only visible when you time yourself.

---

## Open Question For Week 3 (deferred, not answered this week)

*What's the right pace for me — is 1 SD case study per week enough, or should I do 2? What's the diminishing-return point?*

We answer this at end of Week 2 based on how the first full case study went.
