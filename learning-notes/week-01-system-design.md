# Week 1 System Design Exercise — Company Knowledge Search

**Prompt:** *"Design a system that lets engineers at your company search across 5 years of Slack messages, GitHub PRs, and Notion docs using natural language."*

**Constraints given:**
- ~100M Slack messages, ~500K GitHub PRs, ~50K Notion docs
- 500 engineers, searching concurrently at peak
- Continuous content ingestion
- Access controls (private channels)

**Baseline at time of attempt:** SD self-rating 1/5. First formal SD exercise.

> **Framing:** this is a deliberate first attempt, not a finished design. Sections 1-3 completed in full; Section 4 partial; Sections 5-7 deferred. Gaps and coaching notes preserved so the delta between this attempt and future attempts is visible.

---

## Section 1 — Clarifying Questions

Questions I would ask the VP of Engineering before designing.

### What to build (functional scope)
- Are we basically building a data storage layer, and do modelling on top of it so that it will help us to search info about the company?
- Do we need to treat all the data as a single source, or should we label them based on category so we can do category-level search?

### How well it must work (scale, latency, availability, consistency)
- How long is data maintained — 5-year sliding window, or infinite?
- Do we need this system instantly available with new information, or is latency of days/months acceptable?
- How critical is availability — is downtime for part of a day/days OK?
- Is it OK if the system doesn't retrieve the latest info on a particular doc because that content isn't loaded yet?

### Constraints (budget, timeline, infra, security)
- Do we need this in priority now, and is gradual backfill of old data acceptable without losing new data?
- Any specific tools or cloud environment we must use?
- Do we need per-user behavior differences for security?

### Coaching feedback on this section

**Strong:** grouping by intent (what / how well / constraints), asking about retention window, latency tolerance, availability tolerance, prioritization + gradual backfill, per-user access.

**Missing (a stronger candidate would have asked):**
- What does *search* mean here — keyword, semantic, both? Exact quotes vs. natural-language questions?
- What does a *result* look like — list of docs, synthesized answer, or both?
- Peak concurrent QPS — 5, 50, or 500?
- P99 query latency target — 500ms, 2s, 10s?
- Freshness SLA per source (Slack vs. GitHub vs. Notion)?
- Budget envelope?
- Compliance requirements — GDPR, SOC2, retention mandates?
- How do access controls work across the three source systems — mirror per-source, or central identity?
- When content is deleted at source, must search reflect that immediately?

**Framing slips to correct next time:**
- "Are we building a data storage layer?" — guessing the answer instead of asking about the problem
- "Do we need to label data by category?" — design detail, not a scope question

**Meta-lesson:** ask for specific numbers upfront (QPS, P99 latency, freshness SLA, budget). Can't estimate capacity without them.

### Numbers the VP gave me (to unblock Section 2)
- Peak concurrent QPS: 50
- Query P99 target: 1.5 seconds
- Freshness SLA: Slack 5min, PRs 15min, Notion 1 hour
- Retention: 5-year sliding window
- Access controls: Mirror per-source; central SSO (Okta)
- Budget: ~$40k/month all-in
- Availability: 99% (best-effort — internal tool)
- Existing infra: AWS shop; no existing search stack; any managed service OK

---

## Section 2 — Capacity Estimation

### Storage — raw content
| Source | Count | Avg size | Total |
|--------|-------|----------|-------|
| Slack  | 100M msgs | ~200 B | 20 GB |
| PRs    | 500K | ~2 KB | 1 GB |
| Notion | 50K | ~5 KB | 0.25 GB |
| **Total** | | | **~22 GB** |

### Storage — embeddings
- Chunking: Slack 1 vector/msg; PR ~4 chunks/PR; Notion ~10 chunks/doc
- Total vectors: 100M + 2M + 0.5M = **~102.5M vectors**
- Embedding size (OpenAI 3-small): 1536 dims × 4 bytes = 6 KB/vector
- Total: 102.5M × 6 KB ≈ **~615 GB**

### Write throughput
- Slack: 100M msgs / 5yr / 365d / 86400s = ~0.6 msgs/sec avg; ~10 msgs/sec peak
- PRs: ~0.003 PRs/sec avg
- Notion: ~30 docs/day (negligible)

### Query cost
- 35M queries/month peak; embed cost ~$7/month at 3-small
- One-time backfill of 102.5M docs (avg 50 tokens each): 5B tokens ≈ $100 with 3-small

### Read side — latency budget (P99 ≤ 1500ms)
- Embed query: 50-150ms (API) or 10-30ms (self-host)
- Vector search: 10-100ms
- ACL filter + rerank + response: rest of budget
- Total: must be < 1500ms

### The Reframing Insight

The numbers reveal this is **not** a big-data problem:
- ~22 GB raw content — fits on a laptop
- ~615 GB embeddings — one server, not a cluster
- ~10 msgs/sec peak write throughput — trivial
- 50 QPS peak read — small
- Backfill cost: ~$100 — negligible

**This is a small-data problem with an access-control problem stapled to it.** The design should reflect that: managed vector DB, simple ingestion workers, a well-designed auth/permission layer. Not Kafka + Flink + a service mesh.

### Coaching feedback

Sanity-check rates against total volume + time window. Original "100-500 msgs/sec" for Slack was ~1000x too high — quick division would have caught it.

---

## Section 3 — High-Level Architecture

### First attempt (as drawn)

```
                    [Engineer]
                        |
                        v
                    [Query]
                        |
                        v embeds with same model
      [Slack]           |
      [PRs]     -->  [Embedding Model]  -->  [Vector DB]  -->  [Metadata]
      [Notion]
```

### Coaching feedback on this diagram

**Strong:**
- Diagram exists (many 1/5 candidates freeze here)
- Correct that query and docs must embed through the *same* model
- Small number of boxes (didn't over-engineer)
- Actor is shown

**Gaps:**
1. **Read path doesn't close** — nothing points back to the user. No results shown.
2. **No access-control layer** — flagged in clarifying questions but absent from the diagram. Critical omission.
3. **Metadata is drawn downstream of Vector DB** — should be co-located, not downstream. Vector DB returns IDs; metadata store is joined at query time.
4. **No raw content store** — original text needs a source of truth (S3), separate from vectors. Vectors are derived and regenerable; raw must be preserved.
5. **No ingestion pipeline** — sources go straight to embedding model. Missing: fetch, dedupe, ACL resolution.

### What the diagram should look like (reference for next attempt)

```
    [Slack]     [GitHub]    [Notion]
       |           |           |
    webhook   webhook       poll (30min)
       |           |           |
       v           v           v
    +----------------------------------+
    |  Ingestion Workers (per source)  |
    |  - fetch new/updated content     |
    |  - resolve permissions/ACLs      |
    |  - deduplicate                   |
    +----------------------------------+
              |             |
              v             v
     [Raw Content Store]  [Chunker + Embedder]
     (S3 — source of truth)     |
                                v
                         [Vector DB + Metadata]
                         - vector_id → embedding
                         - vector_id → {source, doc_id, ACLs, ts}

    -----  READ PATH  -----
    [Engineer]
       |
       v
    [Search API]  --auth via--> [SSO / Okta]
       |
       v
    [Embed query]
       |
       v
    [Vector search top-k]
       |
       v
    [ACL filter: drop results user can't see]
       |
       v
    [Return ranked results]
```

### Meta-lesson

Every SD diagram must close three loops:
1. **Data in** — how does content get to searchable state?
2. **Query out** — how does a question turn into results?
3. **Deletion / update** — what happens when source content changes?

First attempt addressed loop 1 partially; loops 2 and 3 not covered.

---

## Section 4 — Data Ingestion (Partial)

### Mechanism choices

| Source | Ongoing | Backfill | Updates | Deletes |
|--------|---------|----------|---------|---------|
| Slack  | Webhook | Polling  | Webhook | Webhook |
| GitHub | Webhook | Polling  | Webhook | Webhook |
| Notion | Polling | Polling  | Polling | Polling |

### Coaching feedback

**Mechanisms are right** — real-time webhooks for Slack/GitHub, polling for Notion (limited webhook support, 1hr SLA permits it).

**Section under-specified** — this reads as a mechanism list, not a design. A stronger version would spell out:
- Which specific Slack events to subscribe to (`message.channels`, `message_changed`, `message_deleted`)
- Backfill pagination strategy and estimated duration (100M Slack msgs at ~50 req/min = ~14 days)
- How update events map to vector operations (upsert same vector_id vs. delete-and-recreate)
- How Notion deletes are detected without webhook (weekly reconciliation job)
- The shared ingest pipeline (webhook/poll → SQS → worker → dedupe → resolve ACLs → chunk → embed → write to S3 + Vector DB)

Deferred to a future exercise.

---

## Sections 5-7 — Deferred

Sections skipped this attempt. Placeholders for next iteration:

- **Section 5 — The Retrieval Layer:** auth → query embed → vector search → ACL filter → rerank → response. Latency budget breakdown summing to ≤ 1500ms.
- **Section 6 — Three Biggest Risks:** to be identified after the retrieval layer is designed. Candidates: access-control bypass, embedding drift on model migration, hot-shard latency at 10x scale.
- **Section 7 — What I Don't Know:** ingestion mechanics (webhooks/polling APIs) needed a primer during this exercise. Vector DB internals (HNSW vs IVF, when each), rerank model choice at scale, and RAG-vs-retrieval-only trade-offs are open gaps.

---

## Reflection

**What surprised me:** the reframing insight from Section 2 — that raw content is only ~22 GB and write throughput is trivial. The "5 years of Slack" framing feels big-data; the numbers say it isn't. Most of the interesting complexity is in access controls, not scale.

**What's still fuzzy:**
- Webhook vs polling details in practice (needed a primer mid-exercise)
- Access-control patterns for cross-source permissions (per-doc ACL vs. group-based)
- How rerankers plug into a retrieval flow — timing, latency, model choice
- Read/write path in the diagram — mechanically knew it should close, didn't naturally think of it

**What the exercise felt like:** frustrating in the middle sections when specificity was required. Comfortable at requirements/capacity where the shape was clear. Anxiety-producing at architecture where a diagram had to be committed to.

**One question for next session:** how do stronger candidates practice the muscle of *going deep on one component* rather than staying at the surface across many? The "under-specified" feedback on Section 4 suggests I need reps at deep-dive, not just breadth.

---

## What This Exercise Teaches (for future me)

1. **First attempts are supposed to look like this.** Half the sections are shallow, one is skipped, one asks the wrong questions. The value is in the coached delta, not the artifact.
2. **Ask for specific numbers upfront** — QPS, P99, freshness, budget. Design decisions are blocked without them.
3. **Sanity-check rates against volume + time.** Off-by-1000x is caught by dividing.
4. **Every SD diagram has three loops that must close.** Draw all three or the design is incomplete.
5. **Mechanism list ≠ design.** The *why* and the *how it fits together* is the interview signal.
