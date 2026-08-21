# Capacity Estimation — Cheat Sheet

Step 2 of the SD framework. ~5 minutes in a real interview. Goal: put numbers on the whiteboard so every downstream decision has a *reason*.

Pair with: [`00_framework.md`](./00_framework.md), [`clarifying-questions-cheatsheet.md`](./clarifying-questions-cheatsheet.md).

---

## The Five Numbers Every Design Needs

Answer these five questions. Nothing else. Numbers only.

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | **QPS** (read + write, separate) | Drives sharding, caching, connection pools |
| 2 | **Data volume per day** (raw bytes ingested) | Drives ingestion pipeline sizing |
| 3 | **Storage over time** (1yr, 5yr) | Drives storage tier choice and cost |
| 4 | **Bandwidth** (per node, cluster-wide) | Drives network topology, cross-AZ cost |
| 5 | **Memory footprint** (hot data, caches, indexes) | Drives instance size and count |

Every downstream design decision should trace back to one of these five numbers.

---

## The Unit-Conversion Cheat Card

Memorize these. They save you 30 seconds every estimation and prevent embarrassing math errors.

### Time
```
1 day  = 86,400 seconds ≈ 10^5
1 year = ~30M seconds   ≈ 3 × 10^7
```

### Data sizes
```
1 KB = 10^3 bytes    (1024 exact, ignore for estimation)
1 MB = 10^6 bytes
1 GB = 10^9 bytes
1 TB = 10^12 bytes
1 PB = 10^15 bytes
```

### Common rates (rules of thumb)
```
1,000/day    = 0.01/sec   (basically nothing)
1M/day       = 12/sec     (single-node easy)
100M/day     = 1,200/sec  (needs a queue and workers)
1B/day       = 12,000/sec (needs sharding, real distributed system)
1T/day       = 12M/sec    (planet-scale — hyperscaler territory)
```

**Use these to sanity-check rates against total volume.** Common failure: candidate says "100 msgs/sec" when 100M/5yr = 0.6/sec average. Off by 100x. Interviewer catches it, candidate flails.

---

## Doc / Payload Size Assumptions

State assumptions out loud. Interviewer will push back if unreasonable, but they respect explicit reasoning.

Reasonable defaults for common content:

| Content type | Avg size |
|--------------|----------|
| Chat message (Slack, SMS) | ~200 bytes |
| Tweet / social post | ~500 bytes |
| Email | ~5 KB |
| Wiki page | ~5-10 KB |
| PDF report (short) | ~50-500 KB |
| PDF report (long, 200 pages) | ~2-10 MB |
| Meeting transcript (1hr) | ~50 KB text |
| PR/commit metadata | ~2 KB |
| Image (compressed) | ~100 KB - 5 MB |
| Video (per minute) | ~10 MB (SD), ~50 MB (HD) |
| Row in an OLTP DB | ~1 KB |
| Event (metric, telemetry) | ~200-500 bytes |

---

## Embedding-Specific Math (RAG/search systems)

If your problem uses embeddings, add these calculations:

### Vector size

```
Vector size in bytes = dimensions × 4 bytes  (float32)
```

Common models:

| Model | Dims | Bytes/vector | Sanity |
|-------|------|--------------|--------|
| MiniLM-L6-v2 | 384 | 1.5 KB | tiny |
| MPNet-base-v2 | 768 | 3 KB | small |
| OpenAI text-embedding-3-small | 1536 | 6 KB | standard |
| OpenAI text-embedding-3-large | 3072 | 12 KB | premium |
| Voyage-3, Cohere v3 | 1024 | 4 KB | competitive |

### Chunking overhead

```
Chunks per doc = ceil(doc_size_in_tokens / chunk_size)
Total vectors = docs × avg_chunks_per_doc
```

Common chunk sizes: 256-512 tokens for RAG, ~50 tokens for short-text search.

### Embedding storage

```
Embedding storage = total_vectors × bytes_per_vector
Plus ~2x overhead for HNSW/IVF index structures (M pointers per vector)
```

### One-time backfill cost (embedding API)

```
Total tokens ≈ docs × avg_tokens_per_doc
Cost ≈ tokens × ($ per 1M tokens)

OpenAI 3-small: $0.02 / 1M tokens
OpenAI 3-large: $0.13 / 1M tokens
```

---

## LLM Inference Cost (for RAG systems)

This is often the biggest cost in a production RAG system. Ask about it if it's not given.

```
Per-query LLM cost =
  (input tokens × $/1M input) + (output tokens × $/1M output)

Input tokens ≈ chunk_context (5-10 chunks × 500 tokens each) + system prompt (~500)
             ≈ 3,000-6,000 tokens per query

Output tokens ≈ ~500 (a paragraph)

Claude Sonnet 4:   $3/1M input, $15/1M output
GPT-4o:            $2.50/1M input, $10/1M output
Llama-3-70b (self):~$0.30/1M input + output blended (spot GPU)
```

**Monthly cost:**
```
Monthly LLM cost = queries/month × per-query cost
```

Do this math. Interviewers *love* candidates who bring up LLM inference cost proactively.

---

## The 60-Second Estimation Ritual

Every capacity estimation follows the same shape:

```
1. Start with a headline number (users, docs, or events)
2. Multiply by "per user" or "per doc" rate
3. Divide by time (per day / per second)
4. Multiply by average size to get bytes
5. Multiply by retention to get total storage
6. Sanity-check every rate against total-volume/time
7. Round aggressively
```

Say the math out loud. Show every step. Don't quietly reach for a calculator.

---

## Worked Example — Metrics Platform

```
Users:          100M DAU
Events/user:    50/day
Events/day:     5B     (100M × 50)
Events/sec:     ~60k avg   (5B / 86400)
Peak:           ~180k/sec  (3x avg)

Payload size:   500 bytes/event
Daily volume:   2.5 TB     (5B × 500B)
1-year volume:  ~900 TB    (2.5 TB × 365)
5-year:         ~4.5 PB raw, ~2 PB compressed at 2:1

Read QPS:       10k queries/sec (dashboards, alerts)
Read payload:   10-100 KB per query (aggregate window)

Memory:         hot cache = last 1hr = 60k/sec × 3600 × 500B = ~100 GB
```

Every architecture decision that follows should reference these numbers.

---

## Worked Example — RAG Platform

```
Corpus:         10M docs
Doc size:       avg 20 KB (mix of memos and long reports)
Raw storage:    200 GB

Chunking:       avg 20 chunks/doc (some short, some long)
Total vectors:  200M
Embedding:      1536 dims × 4 bytes = 6 KB/vector
Vector storage: 1.2 TB
Plus HNSW:      ~2x → total ~2.5 TB

Backfill cost:  10M docs × 4k tokens avg = 40B tokens
                × $0.02/1M = $800    (with OpenAI 3-small)

Query volume:   3,000 active users × 8 queries/day = 24k queries/day
Peak QPS:       5k (bursts) — given
Average QPS:    ~200

LLM cost per query:
  Input:  6k tokens × $3/1M    = $0.018
  Output: 500 tokens × $15/1M  = $0.0075
  Total:  ~$0.025 per query

Monthly LLM cost: 24k × 30 × $0.025 = $18k/month

vs $200k/month budget → LLM is ~10% of budget. Fine.
```

---

## Common Traps

1. **Faking precision** — "184,753 events/sec" is silly. "About 180k" is right.
2. **Not sanity-checking rates** — if you say "100 msgs/sec" for 100M messages over 5 years, that's ~1000x too high. Always cross-check total-volume ÷ time.
3. **Forgetting HNSW/IVF index overhead** — embedding storage is not just `n × dim × 4`. Add 2x for index structures.
4. **Skipping LLM inference cost in RAG designs** — this is often the biggest line item. Compute it. Compare to budget.
5. **Ignoring bandwidth costs** — cross-AZ traffic is $0.01/GB. At 1 TB/day cross-AZ, that's $30k/month. Not small.
6. **Not converting to per-second rates** — capacity is always sized per-second. If you have per-day numbers, divide by 86400.
7. **Assuming average = peak** — always ask about peak-to-average ratio. Typical: 3x. Some systems: 10-100x.

---

## The 5-Minute Structure

```
0:00 - 0:30   State assumptions out loud (doc size, chunks per doc, etc.)
0:30 - 2:30   Storage math (raw + derived)
2:30 - 3:30   Throughput math (write + read, average + peak)
3:30 - 4:30   Cost math (backfill + monthly ongoing)
4:30 - 5:00   Sanity check: does each number match the constraints given?
```

Then start Step 3 (High-Level Design) with concrete numbers pinned on the board.

---

## Interview Signal

Interviewer's rubric has a line item roughly: *"candidate reasoned quantitatively about capacity."*

- **Weak:** "we'll scale horizontally as needed"
- **Mid:** "we'll shard by user_id, probably 10 shards"
- **Strong:** "we need 12 shards because 175k writes/sec ÷ 15k writes/sec/shard = 12"

Do the math. Show the math. Reference the math when defending architecture in Step 3-4.

---

## Practice Drills

Take 5 minutes each. No calculator.

1. **Twitter timeline:** 200M DAU, 10 tweets/user/day, 500 bytes/tweet. Total daily volume? 5-year storage?
2. **Uber:** 100M riders, 5M drivers, 20M rides/day, GPS ping every 4 sec during a 20-min ride. Peak GPS write QPS?
3. **Netflix:** 250M subscribers, 2hr avg watch time/day, 5 Mbps average bitrate. Bandwidth requirement?
4. **Slack:** 10M workspaces avg 50 users, 30 msgs/user/day, 200 bytes/msg. Daily message volume across the platform?

Do 3 of these a week for a month and estimation becomes muscle memory. Zero cost, high leverage.
