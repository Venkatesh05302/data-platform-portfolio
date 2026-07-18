# Senior → Staff DE Roadmap (v2 — Recalibrated)

> **Target:** Switch to a top product company in 6-12 months.
> **Pace:** 6-10 hrs/week (~8 hrs median).
> **Stack anchor:** AWS (Redshift, EMR, Glue, S3) — skills must transfer.
> **Start date:** 2026-06-30.
> **Baseline (Week 1):** Spark 3/5 · SQL 4/5 · System Design 1/5 · AI/LLM 1/5

---

## What Changed in v2 (and Why)

After your self-assessment, I rewrote the roadmap. Here's the diff:

| Area | v1 Plan | v2 Plan | Reason |
|------|---------|---------|--------|
| System Design | Phase 2 (Month 4-5) | **Phase 1 (Month 1+) — Track A** | SD at 1/5 is your biggest interview risk. It compounds slowly. Start now. |
| AI / LLM | Track A | **Track B (parallel with SD)** | Still high priority, but no longer alone in the lead slot. |
| Spark / Distributed Systems | Track B (3 hrs/wk) | **Supporting Track (~1.5 hrs/wk)** | At 3/5 you're competent. We deepen *where SD demands it*, not as standalone study. |
| SQL | Track C (2 hrs/wk) | **Maintenance (~1 hr/wk)** | At 4/5 you don't need heavy study. Solve 2-3 hard problems weekly to stay sharp. |
| Streaming / Kafka | Phase 2 | Phase 2 (unchanged) | Builds on SD foundation. |

**The principle:** invest hours where the *marginal return* is highest. Two 1s and a 4 means we don't spread evenly — we concentrate.

---

## Weekly Time Allocation (Phase 1)

```
~8 hrs/week breakdown:
  ┌──────────────────────────────────────┐
  │ System Design          ~3.0 hrs       │  ← Biggest gap, slowest compounding
  │ AI / LLM               ~3.0 hrs       │  ← Biggest gap, fastest portfolio impact
  │ Spark / Distributed    ~1.5 hrs       │  ← Topical, tied to current SD problem
  │ SQL                    ~0.5 hrs       │  ← Maintenance only (2-3 hard Qs)
  └──────────────────────────────────────┘
```

If you only get 5 hours one week, drop SQL and Spark; keep SD and AI.

---

## The Strategy (Why This Roadmap Looks Different)

Most DEs with 7 years of experience get stuck because they keep *adding* tools instead of *deepening* the fundamentals interviewers actually probe. At top product companies, the bar for a Senior/Staff DE is:

1. **System design fluency** — can you design a real platform (not draw boxes) with trade-offs? ← your biggest gap
2. **AI-native engineering** — RAG, vector DBs, AI pipelines. New bar in 2026. ← your other gap
3. **Distributed systems thinking** — Spark shuffle, Kafka partitioning, consistency models
4. **Data modeling depth** — dimensional, Data Vault, OBT trade-offs
5. **Code quality** — engineers, not just pipeline operators
6. **Communication** — design docs, technical writing, behavioral stories

We optimize for #1 and #2 first because they're your weakest and they unlock the others.

---

## Phase 1 — Close the Two Big Gaps (Month 1-3)

### Track A — System Design (~3 hrs/week)

This is your highest-leverage investment. We follow a "framework + reps + critique" loop.

**Month 1: The Framework + First Designs**
- Learn a **6-step system design framework** for data platforms (Requirements → Scale Estimation → API/Data Model → High-Level Architecture → Deep Dives → Bottleneck Analysis). I'll teach this Week 2.
- Read 3 canonical designs deeply (I'll provide):
  - Real-time analytics (e.g., orders/min dashboard)
  - Batch + serving (e.g., feature store)
  - Search/retrieval (e.g., e-commerce product search)
- For each: **sketch your own version first**, *then* read the canonical. Compare. This builds judgment, not memorization.

**Month 2: 5 More Designs + First Mock**
- Stripe-style fraud detection pipeline
- Uber-style surge pricing analytics
- Netflix-style viewing event pipeline
- Slack-style message search
- Notion-style real-time collaboration data layer
- **Mock #1** with me at end of Month 2 — I role-play as a Staff interviewer.

**Month 3: Trade-off Mastery + Mock #2**
- Deep dives on critical trade-offs: Lambda vs Kappa, Lakehouse vs Warehouse, CDC vs full snapshots, push vs pull metrics, sync vs async APIs, schema-on-read vs schema-on-write.
- 3 more designs, this time with realistic constraints ("you have $50K/month budget", "team of 4 engineers").
- **Mock #2** — by end of Month 3 you should be able to do a credible 45-min SD round.

### Track B — AI / LLM for Data Engineers (~3 hrs/week)

**Month 1: Foundations**
- Embeddings (Week 1 — you're doing this now)
- LLM mental model: tokens, context window, temperature, function calling, structured outputs
- Prompt engineering for *production* (not chat) — few-shot, chain-of-thought, JSON mode
- Build a tiny RAG over your own notes by end of Month 1

**Month 2: RAG Architecture in Depth**
- Chunking strategies (fixed, semantic, recursive, parent-document)
- Retrieval methods: dense, sparse (BM25), hybrid, reranking with cross-encoders
- Vector DB comparison: pgvector vs OpenSearch k-NN vs Pinecone — what AWS-native shops actually pick
- LLM evaluation: RAGAS, golden datasets, hallucination metrics
- **Capstone start:** AWS-native RAG pipeline (S3 → embedding → OpenSearch → API)

**Month 3: AI Pipelines & Agents**
- Treating RAG ingestion as ETL: backfills, incremental updates, deletes, embedding drift
- MCP (Model Context Protocol) — what it is, why it matters for data teams
- AI agents: when they make sense for data tasks, when they don't
- **Capstone finish:** Ship the RAG project with a write-up. This becomes a portfolio anchor.

### Supporting Track — Spark / Distributed Systems (~1.5 hrs/week)

Topical, not sequential. We deepen the area that's currently relevant to the SD design you're working on. Examples:
- Working on a "design a batch pipeline" → we go deep on Spark shuffle, AQE, partitioning
- Working on streaming design → we cover Kafka partitions, Spark Structured Streaming internals
- Working on lakehouse design → we cover Iceberg vs Delta vs Hudi internals

This makes the learning *applied*, which is how senior engineers think anyway.

### Maintenance — SQL (~0.5 hrs/week)

Solve 2-3 hard SQL problems per week. I'll send curated ones. Focus on patterns that show up in interviews:
- Sessionization
- Top-N per group with ties
- Gap-and-island problems
- Running totals with complex windowing
- Pivoting dynamic columns

---

## Phase 2 — Streaming Depth + More System Design (Month 4-5)

By now you have a working SD framework and ~10 designs under your belt. Time to add the streaming dimension that top product companies almost always test.

- **Kafka deep dive:** partitions, consumer groups, exactly-once, transactions, KRaft, ISR
- **Streaming patterns:** windowing (tumbling, sliding, session), watermarks, late data, stateful processing
- **Flink vs Spark Structured Streaming** — Flink wins for stateful, low-latency; Spark for unified batch/stream
- **CDC patterns:** Debezium, AWS DMS, log-based vs trigger-based
- **Event-driven architecture** for data platforms
- **10 more system designs** with streaming components
- **Mock #3** — full 60-min mock combining SD + streaming + behavioral probes

---

## Phase 3 — SWE Polish + Behavioral (Month 5-6)

Top product companies hire DEs as *engineers* first.

- **Python at senior level:** typing, async, packaging, profiling, pytest strategies
- **Design patterns relevant to DE:** Strategy, Factory, Repository, Observer for event-driven
- **Testing data pipelines:** unit, integration, data quality (Great Expectations / Soda), contract testing
- **CI/CD for data:** dbt CI, Spark testing, lakehouse migrations
- **IaC with Terraform** for data platforms
- **Behavioral prep:** Draft 8 STAR stories — leadership, conflict, ambiguity, failure, scope, mentorship, influence, technical depth
- **Resume rewrite** at Staff-level framing (scope, impact, scale)

---

## Phase 4 — Job Hunt Execution (Month 6-12)

- Portfolio polish — 2 anchor projects with write-ups (RAG pipeline + streaming platform)
- LinkedIn / referral strategy
- Application targeting: tier-1 (FAANG, top unicorns), tier-2 (strong product companies), tier-3 (backup)
- **Mock interviews weekly:** SD, coding, behavioral
- Offer negotiation strategy (this alone can be worth $50K+)

---

## How We'll Work Together Each Week

Expect from me every week:
1. **System Design topic of the week** — one design or one framework piece
2. **AI/LLM topic of the week** — one concept + hands-on
3. **Spark/SQL micro-content** — what's currently relevant
4. **Interview question** — to keep market-ready muscle warm
5. **Honest assessment** — what's improving, what's not

Every 4 weeks: re-take the 1-5 self-assessment so we can see real movement.

---

## Honest Risk Assessment

Given your baseline:

**Strengths going in:**
- 7 years of production DE — you bring real war stories that fresh grads can't
- SQL at 4/5 — most senior candidates underestimate SQL prep; you don't have to
- Spark at 3/5 — solid working foundation to build internals on

**Risks:**
- **System Design at 1/5 in 6 months is aggressive.** Doable, but only if SD gets the 3+ hours/week consistently. Skipping SD weeks is the #1 failure mode.
- **AI/LLM at 1/5 means the RAG capstone is essential** — without a tangible AI project, you'll struggle to back up "I know AI" claims in interviews.
- **Behavioral round is often underestimated** — we won't make that mistake.

**Confidence:** With consistent 8 hrs/week and honest follow-through, you'll be interview-ready for tier-2 product companies by month 5 and tier-1 by month 8-10.

---

## Next Step

Open `01_WEEK_1.md` — I've added a System Design seed exercise to this week's plan, so you start that muscle immediately.
