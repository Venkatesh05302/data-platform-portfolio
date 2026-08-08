# System Design Interview Framework

A structured 6-step approach to any 45-minute system design interview. Applies to product-company Senior/Staff Data Engineering loops (Meta, Google, Amazon, Netflix, Uber, Airbnb, Stripe, Databricks, Snowflake).

## Why a framework

An unstructured System Design interview fails in the first 5 minutes — the candidate starts drawing boxes before understanding what they're building, then spends 40 minutes discovering (from their own contradictions) that the design doesn't handle a requirement they never verified existed.

A framework gives you three things:

1. **Recovery path under stress** — even when the prompt is unfamiliar, you know what to do next.
2. **Score legibility** — the interviewer's rubric maps 1:1 to a good framework. They know where in their notes to write down your points.
3. **Signal of seniority** — anyone can draw boxes. Not everyone can drive a 45-minute conversation with structure.

## The framework at a glance

```
Step                          Time      Goal
────────────────────────────────────────────────────────────────
1. Requirements               5-7 min   Know exactly what you're building
2. Capacity Estimation        5 min     Get numbers on the whiteboard
3. High-Level Design          8-10 min  Draw the boxes with justification
4. Deep Dive                  15 min    Zoom into 1-2 components
5. Trade-offs & Alternatives  5 min     Show you can defend the design
6. Follow-ups / Scale         5 min     What breaks at 10x?
────────────────────────────────────────────────────────────────
Total                         ~45 min
```

Notice the shape: **most time in the middle (deep dive), not the beginning (architecture).** Inverting this ratio is the single biggest mistake candidates make.

---

## Step 1 — Requirements (5-7 minutes)

**Goal:** understand exactly what you're building. Establish scope, users, and what "done" looks like.

Split requirements into three explicit buckets. State each back to the interviewer. Get confirmation.

### 1a. Functional requirements

- Who are the users?
- What are the top 3 things they need to do?
- What's explicitly *out of scope*?

Write these as a bulleted list on the board. This is your contract.

### 1b. Non-functional requirements — the four pillars

| Pillar | Questions to ask |
|--------|------------------|
| Scale | How many users? Data ingested/day? Peak vs average? |
| Latency | Read P50/P95/P99? Write P50/P95/P99? |
| Availability | How many 9s? Cost of downtime? |
| Consistency | Strong, eventual, read-your-writes, or bounded staleness? |

**Interview trap:** P99 latency matters more than average in data systems. Average hides the tail; users notice the tail.

### 1c. Constraints and assumptions

- Team size (informs simplicity vs sophistication)
- Timeline (MVP vs production)
- Budget ($$ matters at senior+)
- Existing infrastructure to leverage or work around

### What the whiteboard should look like at end of Step 1

```
FUNCTIONAL
  - Users can X, Y, Z
  - Not doing: A, B (out of scope)

NON-FUNCTIONAL
  - Scale:        100M users, 5B events/day
  - Latency:      read P99 < 300ms, write P99 < 1s
  - Availability: 99.95% (~4.4 hrs/year downtime)
  - Consistency:  read-your-writes for author, eventual for others

CONSTRAINTS
  - AWS-primary
  - 3-person team, MVP in 8 weeks
```

---

## Step 2 — Capacity Estimation (5 minutes)

**Goal:** put numbers on the whiteboard. Numbers drive every subsequent decision.

Compute these five values out loud, using round numbers:

1. **QPS** — read QPS and write QPS separately
2. **Data volume per day** — raw ingested bytes
3. **Storage over time** — 1 year, 5 years
4. **Bandwidth** — per node, cluster-wide
5. **Memory footprint** — for hot data, caches, indexes

### Worked example — "design a metrics platform"

```
Users:           100M DAU
Events/user:     50/day
Events/day:      5 x 10^9 = 5B/day
Events/sec:      5B / 86400 = ~58k events/sec average
Peak:            3x average = ~175k events/sec

Payload size:    500 bytes/event
Daily volume:    5B × 500B = 2.5 TB/day
1-year volume:   ~900 TB
5-year volume:   ~4.5 PB raw, ~2.2 PB compressed at 2:1

Read QPS:        ~10k queries/sec (dashboards, alerts)
Read payload:    10-100 KB per query (aggregate windows)
```

**Interview signal:** every downstream architecture decision should reference these numbers.

- Weak: "we'll shard"
- Strong: "we need 12 shards because 175k/sec ÷ 15k/sec/shard = 12"

**Common mistake:** faking precision. "175,384 events/sec" is silly. "About 175k" is right.

---

## Step 3 — High-Level Design (8-10 minutes)

**Goal:** draw 5-8 boxes with data flow, and justify each with a *reason*.

### Rules for a good diagram

1. Data flow left-to-right or top-to-bottom. Never chaotic.
2. Every arrow has a direction and a *contract* ("Kafka → Flink" is "events consumed at ~180k/sec, checkpoint every 30s").
3. Every component has a one-line justification. Not "we use Kafka" — say *"Kafka gives us durability, replay, and decouples ingest from processing."*
4. Storage is explicit: cold vs hot, source of truth vs derived, hot cache vs primary.
5. Include the client. Every system serves a user.

### Example — metrics platform

```
   [Mobile/Web Clients]
           |
           v
   [API Gateway / Ingest Layer]   rate limiting, auth, backpressure
           |
           v
   [Kafka]                        durable event log, decouple write/read
           |
           +--------------+
           v              v
   [Stream Processor]  [Batch Archive → S3]
   (Flink/Spark)         long-tail analytics, backfill
           |
           v
   [OLAP Store]                   Druid/ClickHouse, sub-second aggregates
           ^
           |
   [Query Layer / API]            auth, quota, caching
           ^
           |
   [Dashboards / Alerts]
```

**Common mistakes:**

- Too much detail — save partition strategy for Step 4
- Missing the read path OR the write path
- Vague components ("Database" is a shrug; "Postgres for user profiles, Cassandra for events" shows fit-aware reasoning)
- Ignoring the client

---

## Step 4 — Deep Dive (15 minutes — the most important step)

**Goal:** prove technical depth in 1-2 components. This is where the interview is won or lost.

### Signal you want to send

*"There are three interesting components here — Kafka partitioning, OLAP shard strategy, and the query cache. I want to spend most of the time on shard strategy because that's where the hardest trade-offs are. Sound good?"*

You just demonstrated: (a) you know where difficulty lives, (b) you're partnering with the interviewer.

### The 5 flavors of hard questions in DE systems

| Difficulty flavor | Where it hides | What to discuss |
|-------------------|----------------|-----------------|
| Hot partitioning | KV/NoSQL/queue | Composite keys, salting, adaptive splitting, jump hash |
| Consistency | Multi-region, replication | Strong vs eventual, quorum reads/writes, CRDTs, LWW |
| Backfill / reprocessing | Streaming pipelines | Lambda vs Kappa, replay from Kafka, deterministic outputs |
| Schema evolution | Data warehouse, event schemas | Avro/Protobuf, back/forward compat, schema registry |
| Exactly-once semantics | Streaming with side effects | Idempotency keys, transactional writes, dedup windows |
| Cost optimization | High data volume | Cold/hot tiers, compression, retention, aggregation |

Pick 1-2 flavors that fit the problem. Go deep on mechanisms, not names.

### What "deep" actually looks like

**Weak:** "We'll use Kafka."

**Mid:** "We'll use Kafka partitioned by user_id."

**Strong:**
> "We'll use Kafka partitioned by user_id. That gives us per-user ordering, which we need for read-your-writes. But it creates a hot-partition risk for our top 100 users — a top influencer alone might be 5% of traffic. So we'll compound the partition key with a bucket suffix — `user_id || (event_ts // 60s)` — which spreads a single user across up to 60 partitions per minute. Trade-off: per-user ordering is preserved within a bucket but not across buckets, which is fine for our use case because ordering only matters at the second level. If we needed strict global ordering, we'd use a single partition per user and accept hot-partition risk, then mitigate at the consumer side."

Notice: specific mechanism, real trade-off named, alternative acknowledged.

---

## Step 5 — Trade-offs & Alternatives (5 minutes)

**Goal:** volunteer trade-offs *before* being asked. Show you evaluated alternatives.

### Sample dialogue

> "A few decisions I want to flag as trade-offs:
> - I chose Druid over ClickHouse. Druid handles high-cardinality aggregations and has native rollup for older data. ClickHouse would be faster for single-tenant queries but has weaker rollup story.
> - I chose Kafka over Kinesis. On AWS, Kinesis is less ops burden, but Kafka has stronger stream-processing ecosystem and no per-shard limits. Since we already run Kafka for other services, marginal ops cost is low.
> - I chose to keep raw events in S3 for 5 years. Cost is real (~$200k/year) but enables backfill and regulatory audit. If cost was a hard constraint, we'd downsample to 1-min aggregates after 90 days."

### Common mistakes

- Naming trade-offs without depth ("we could also use X" — but not saying *why not*)
- Only acknowledging cheap trade-offs ("bigger cache") instead of architectural ones (CRUD vs event sourcing)
- Refusing to admit any weakness

---

## Step 6 — Follow-ups / Scale / Failure Modes (5 minutes)

**Goal:** show you think about what breaks. Staff engineers spend disproportionate time here.

Volunteer at least three:

- **Scale:** "At 10x our current numbers, the OLAP store's memory exceeds one node. Introduce a coordinator layer and shard by metric_id."
- **Failure modes:** "If Kafka goes down, ingest layer needs to buffer to disk for 15 min minimum. Add SQS as fallback or use MSK multi-AZ."
- **Backfill:** "Late-arriving events accepted within 2-hour watermark. Beyond that, nightly batch job reprocesses the day."
- **Migration:** "Rolling out a new schema: dual-write for a week, flip readers, then decommission old."
- **Monitoring:** "Key SLIs are ingest lag, query P99, OLAP shard hotspots. Alert on lag > 30s and P99 > 1s for 5 min."
- **Cost knobs:** "Three biggest cost drivers are S3 storage, OLAP memory, cross-AZ bandwidth. Set retention/compaction policies accordingly."

Pick 2-3 most relevant to your design.

---

## The Four Meta-Rules

### Rule 1 — Numbers over adjectives
Never "large scale." Say "180k writes/sec." Never "fast." Say "P99 under 300ms."

### Rule 2 — Structure over content
Interviewers remember a well-structured "meh" design more favorably than a chaotic brilliant one. Signal you can drive a 45-minute meeting.

### Rule 3 — Trade-offs over solutions
Every technical choice has a cost. If you can't name the cost, you don't understand the choice.

### Rule 4 — Ask the interviewer
At every step: *"Does this direction make sense? Should I go deeper on X or move to Y?"* Collaboration scores higher than lecturing.

---

## Memorize this timer

```
0:00 - 0:07   Requirements
0:07 - 0:12   Capacity
0:12 - 0:22   High-Level Design
0:22 - 0:37   Deep Dive        ← the meat
0:37 - 0:42   Trade-offs
0:42 - 0:45   Follow-ups
```

If you're at 0:20 and still in Requirements, something is wrong. If you're at 0:35 and still drawing the high-level, something is wrong.

---

## Top 10 killer mistakes

1. Diving into architecture before understanding requirements
2. Name-dropping 15 tools (looks like insecurity)
3. Not asking clarifying questions
4. Silent on trade-offs
5. Panicking when interviewer probes (probes are gifts)
6. Verbal-only answers (always draw)
7. Forgetting the client
8. Overengineering the MVP
9. Underengineering at scale
10. Ignoring cost

---

## How to practice this framework

Reading it once accomplishes nothing. Practice looks like:

1. **Take a prompt** ("Design a real-time metrics platform," "Design a document search system," "Design a feature store").
2. **Set a 45-minute timer.**
3. **Follow the framework on paper or whiteboard**, keeping to the time budget per step.
4. **Record yourself explaining the design out loud** — 5-minute summary at the end.
5. **Play back the recording.** Where did you ramble? Where did you skip a step? Where did numbers save you or expose you?
6. **Write the design as a doc** in this folder (`system-designs/01_...md`, `02_...md`). One doc per case study. This is what makes your portfolio real.

Aim for one design a week. In 8 weeks you have 8 written designs and 8 recorded practice runs — pattern recognition starts kicking in around case 4-5.

---

## Case studies planned in this folder

- `01_rag_platform.md` — Search + Q&A over 10M enterprise docs, 5k QPS, <500ms
- `02_event_ingestion.md` — Segment-style event ingestion at 100M users, 5B events/day
- `03_data_warehouse_internals.md` — Redshift/Snowflake-style columnar OLAP
- `04_streaming_metrics_platform.md` — Real-time metrics like Datadog/Prometheus
- `05_feature_store.md` — Uber Michelangelo / Tecton-style feature platform

Each case study lives as its own markdown file with sections mirroring the framework above.
