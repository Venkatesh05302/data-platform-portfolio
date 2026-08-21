# SD Case Study #1 — Enterprise RAG Platform

**Prompt:** Design an enterprise RAG platform for 8,000 employees at a consulting firm. Search across ~10M internal documents. Return synthesized answers with citations, not just document links. P99 latency 3 seconds. Per-doc access controls. SOC 2 + GDPR compliance. $200k/month budget.

**Baseline at time of exercise:** SD self-rating ~1.5/5 (post-Week-1). Second full case study attempt.

**Framing:** deliberate practice, not a finished design. All 7 sections attempted for the first time. Coaching notes preserved so gaps and improvements are visible for future me.

---

## Section 1 — Clarifying Questions

### Functional (what to build)
- Does the user have an option to search in a particular category?
- Do we have any priority of which source to consider as source of truth if multiple files have different results?
- What kinds of questions can users ask — direct factual lookups, or always semantic requests?
- What if the information is not available in the corpus?

### SNAP (specific numbers)
- 10M docs — how many years of data? Retention going forward?
- Is there a chance user count will grow?
- Peak was mentioned as 5,000 QPS — what's the average?
- Is 3-second latency inclusive of all operations (embed query + vector search + LLM inference)?
- How fast must new content be refreshed — same for all source types?
- What's the budget range?

### Unique (this problem's hard parts)
- Do users of different roles / engagement teams have different data visibility?

### Coaching notes on this section
- **Strong:** caught the numbers already given in the prompt; asked only about gaps. Latency-inclusive-of-all-ops question is a strong senior move.
- **Missing:** Users bucket entirely absent — should have asked about daily active count, usage pattern, retry behavior. Unique bucket thin — only 1 question when this is the hardest problem in the design.
- **Meta-lesson:** every SD problem needs SNAP (Scale, Network, Availability, Purse) + 5 buckets (Functional, Non-functional, Users, Constraints, Unique). Don't skip the Users bucket.

### Sponsor's answers (used for Sections 2+)
- **Functional:** synthesized paragraph + citations; ~20% direct lookups; source-of-truth = most-recent doc unless marked canonical; must refuse ("I don't have information") rather than hallucinate.
- **SNAP:** 15 years of corpus, ~500K new docs/year; peak 5k QPS burst, average ~200 QPS sustained; 3s P99 total end-to-end; Wikis 15min / deliverables 1hr / transcripts 4hr freshness; $200k/mo; 99.5% availability (internal, business hours).
- **Users:** 8k employees, 3k daily active, 8 queries/day/user, 2-3 rephrases if answer is off.
- **Unique:** LLM must be SOC 2 Type II attested (Claude/GPT-4/self-host Llama-3-70b all OK); Okta SSO + separate staffing service; revised docs must disappear from answers within 1 hour; GDPR data residency (EU stays in EU).

---

## Section 2 — Capacity Estimation

### Raw storage
- 10M docs × ~500 KB avg = **~5 TB**
- Assumption: doc sizes range 2 KB to 2 MB; avg ~500 KB

### Embedding storage
- Chunking: assume ~20 chunks/doc average (mix of short memos and long reports)
- Total vectors: 10M × 20 = **200M**
- Vector size: 1536 dims × 4 bytes = 6 KB/vector (OpenAI text-embedding-3-small)
- Total: 200M × 6 KB = **~1.2 TB**, +HNSW overhead ~2x → **~2.5 TB total vector-side**

### One-time backfill cost
- 10M docs × ~4,000 tokens avg = 40B tokens
- 40B × $0.02/1M = **~$800 one-time** to embed the whole corpus

### Ongoing ingestion cost
- 500K new docs/year × 4,000 tokens × $0.02/1M = **~$40/year** (~$3.30/month)
- Trivial at this scale

### Query volume
- 3,000 active users × 8 queries/day = **24,000 queries/day**
- Monthly: 720,000 queries/month
- Sustained rate: ~1 QPS during business hours
- Peak burst: 5,000 QPS (given — bursts, not sustained)
- Design implication: size infra for sustained, buffer for burst

### Monthly LLM inference cost
- Per query: ~6,000 input tokens (5-10 retrieved chunks × 500 tokens + system prompt) + ~500 output tokens
- Claude Sonnet: 6k × $3/1M + 500 × $15/1M = $0.018 + $0.0075 = **~$0.025/query**
- Monthly: 720K × $0.025 = **~$18,000/month**
- vs. $200k budget → LLM is ~9% of budget → comfortably fits

### Total monthly cost (rough)
```
Storage (S3 + Vector DB):          ~$500-2k
Ingestion embedding:                ~$3
Query embedding:                    ~$0.30
LLM inference:                      ~$18,000
Vector DB compute:                  ~$3,000
Application compute:                ~$5,000
Bandwidth + misc:                   ~$1,000
                                    ─────────
Total:                              ~$27,500/month
Budget:                             $200,000/month
Headroom:                           ~86% unused
```

### Coaching notes
- **Strong:** correct storage math, correct instinct on peak vs average QPS. Asked when confused about "backfill cost."
- **Errors caught:** vector size (used 10 KB, should be 6 KB); chunks per doc (used 100, should be ~20); daily query math (calculated 155M/day, should be 24k — misinterpreted peak QPS as sustained).
- **Design insight:** at this scale, LLM inference is the biggest ongoing cost. Backfill is negligible. Bandwidth/storage are rounding errors. Design has 86% budget headroom → can afford premium models, caching layers, multi-region, reranking, human-in-the-loop review.

---

## Section 3 — High-Level Architecture

### First attempt

```
[New Data] → [S3 Raw Storage] → embeds → [Vector DB]
                                            ↓
                                        [Reranker] → [LLM]
                                            ↑              ↓
                                        [ACL Check]    [Portal]
                                            ↑              ↓
                                        [Portal] ← Ask question ← [Actor]
```

### Coaching notes
- **Strong:** read path closes (Actor → Portal → ACL → Vector DB → Reranker → LLM → Portal → Actor). Raw storage separate from Vector DB. ACL check as distinct component. Reranker included.
- **Gaps:** ACL positioned before vector search (should be after or as pre-filter *inside* the search); missing ingest worker (chunker, embedder, ACL-resolver as explicit boxes); missing query embedder in read path; missing SSO/staffing-service auth source.

### Reference architecture (for next attempt)

```
==========  WRITE PATH  ==========
[Source systems] → [Ingest Worker: fetch, dedupe, resolve ACLs, chunk]
                        ↓                              ↓
                [Raw Content Store (S3)]      [Embedder]
                                                        ↓
                                              [Vector DB + Metadata]
                                              vector_id → {embedding, acl_groups, doc_id, ts}

==========  READ PATH  ==========
[Actor] → [Query Portal / API] ← auth via → [Okta SSO + Staffing Service]
              ↓
      [Query Embedder]
              ↓
      [Vector DB search top-K=100] ← pre-filter by user's ACL groups
              ↓
      [ACL Filter (post-check)]
              ↓
      [Cross-Encoder Reranker (top-100 → top-10)]
              ↓
      [Prompt Assembly: system prompt + top-10 chunks + user question]
              ↓
      [LLM (Claude Sonnet)]
              ↓
      [Answer + Citations → Actor]
```

---

## Section 4 — Deep Dive: Access Control Layer

### Why interesting
Access control is the hardest problem in this system. Correctness is non-negotiable (leaking a confidential engagement is career-ending and a lawsuit). Must not blow 3s latency budget. Permissions change hourly (consultants staff on/off engagements).

### Design choice — pre-filter via metadata on vectors
At ingest time, resolve each doc's ACL from source system + staffing service. Store as vector metadata:
```
{ vector_id, embedding, doc_id, acl_groups: ["engagement_A", "public"] }
```
At query time:
1. Look up user's current ACL groups from staffing service (cached 60s)
2. Send vector search with pre-filter: `{ must: [{ any: { acl_groups: [user_groups] } }] }`
3. Vector DB returns only vectors whose acl_groups intersect with user's allowed groups
4. Log `{ user_id, timestamp, query, returned_doc_ids }` to S3 for audit

### Trade-off — pre-filter vs post-filter
- Pre-filter: search space is restricted → faster and correct by construction. Requires vector DB to support metadata filtering (Qdrant, Pinecone, pgvector all do).
- Post-filter: search all vectors → drop unauthorized after. Universal support but wasteful — if 95% of docs are unauthorized, you'd need top-2000 candidates for 100 usable results.
- Chose pre-filter given Qdrant support + high ACL sparsity.

### Failure modes
1. Staffing service down → **fail closed** (return no results). Compliance-safe. User sees "search temporarily unavailable."
2. User's ACL changed mid-session → up to 60s stale cached permissions. Acceptable given hourly cadence.
3. Doc's ACL changes after indexing → up to 5min stale if TTL alone. Mitigate with explicit invalidation via SNS on ACL-change event.
4. In-flight race (user removed while query executes) → rare, logged, acceptable.

### Numbers
- ACL lookup (cached): ~5ms
- Pre-filter overhead in vector search: ~10-20ms
- Audit log write: async, off critical path
- Total ACL cost: ~15-25ms out of 3000ms budget → <1%

### Audit
- Every query logs `{ timestamp, user_id, query, returned_doc_ids, user_acl_groups_at_query_time }` to S3 append-only
- Weekly reconciliation job replays each returned_doc_id against permission snapshot → flags any inconsistency
- Retention: 7 years for SOC 2

### Coaching notes on this section
- **First attempt** was directionally right on mechanism but empty on trade-off, alternatives, failure modes, numbers — the parts that actually win interviews.
- **Meta-lesson:** a deep dive isn't showing what you know; it's showing you've *interrogated your own design*. Three interview prompts unlock this: "What breaks?" "What's the naive alternative and why isn't it good enough?" "What's the cost of my choice?"

---

## Section 5 — Trade-offs & Alternatives

### Trade-off 1: Pre-filter vs post-filter for ACL
- **Chose:** pre-filter
- **Gave up:** performance predictability across vector DBs; HNSW recall degrades when a small fraction of vectors pass the filter (e.g., 1% pass → recall drops sharply as HNSW's graph doesn't have enough authorized neighbors in the hop path)
- **When flips:** if permissions become very sparse (<1% of corpus per user), switch to per-user partitioned indexes

### Trade-off 2: Separate staffing service vs. denormalized ACL on vectors
- **Chose:** keep staffing service separate; look up user's ACL groups at query time
- **Gave up:** added latency (extra service hop per query) and coupling to staffing service availability
- **Gained:** staffing is authoritative; embedding ACLs into every vector would mean propagating every staffing change to millions of vectors
- **When flips:** if staffing service becomes a latency bottleneck (P99 >100ms), denormalize by writing ACL groups into vector metadata at ingest + scheduled refresh

### Trade-off 3: 60-second ACL cache TTL
- **Chose:** 60s cache TTL on user ACL groups
- **Gave up:** up to 60s stale permissions after change
- **Gained:** staffing service load drops ~1000x
- **When flips:** if compliance requires <5s propagation, reduce TTL to 5s AND add event-driven invalidation via SNS on ACL-change events

### Coaching notes
- **Structure locked in:** all three have the three-part shape (what/gave-up/when-flips).
- **Sharpening needed:** name specific mechanisms that fail (HNSW recall under selective filters), not just categories ("vendor lock-in"). "Less X" is a category; "specific X breaks under condition Y" is a trade-off.

---

## Section 6 — Three Biggest Risks

### Risk 1: Hallucination on high-stakes queries
- **What breaks:** LLM synthesizes an answer using entities/facts not in retrieved context, and the consultant cites it to a client
- **Why matters:** Reputation + legal risk. Consulting firm's product is trust.
- **Mitigation (layered):**
  1. System prompt: "Answer only from context. If insufficient, respond 'I don't have information on that.'"
  2. Grounding check: post-generation validator ensures every claim in answer appears in retrieved chunks
  3. Required citations: UI shows source snippet alongside each claim
  4. User feedback loop: thumbs-down flags query/retrieval/answer for eval-set addition
  5. Confidence threshold: if top chunk cosine < 0.6, prepend "Limited context — verify before citing"

### Risk 2: Retrieval quality decay over time
- **What breaks:** corpus shifts, user language evolves, model drifts — retrieval quality slowly degrades
- **Why matters:** confidence erodes silently; users complain "answers used to be better"
- **Mitigation:**
  - Golden eval set: 200-500 labeled query-doc pairs, held constant; nightly run against production
  - Alerts: recall@5 drop >5% relative vs. rolling 7-day baseline → PagerDuty
  - Feedback loop: thumbs-down rate per week per topic; spikes signal topical drift
  - Refresh cadence: eval set augmented monthly with 20 new queries sampled from real traffic, labeled by SMEs
  - Response menu: retrain reranker | re-embed newer docs | update chunking — eval set diagnoses which layer decayed

### Risk 3: Embedding model deprecation
- **What breaks:** provider announces embedding model EOL; stored vectors incompatible with new query vectors
- **Why matters:** search accuracy collapses if not migrated cleanly; migration itself risks downtime
- **Mitigation:**
  - Raw content in S3 = source of truth; vectors always regenerable
  - Dual-embedding plumbing from day one: ingestion supports writing to two indexes via feature flag
  - 90-day migration playbook: shadow index → prioritized backfill → dual-write → shadow eval → gradual traffic shift → decommission
  - Contractual clause: vendor must give 12-month deprecation notice (real enterprise ask)

### Coaching notes
- **Strong:** all three risks are design-specific, not generic. Naming model deprecation is a direct payoff from Week 1 drift/migration study.
- **Sharpening needed:** mitigations name outcomes ("strong prompt", "check periodically", "be ready to migrate") rather than mechanisms (grounding validators, golden eval sets, 90-day playbooks).
- **Interview prompt to internalize:** "How, specifically, does this mitigation trigger and execute?" If the answer is a verb, push one level deeper for the mechanism.

---

## Section 7 — What I Don't Know

### Gap 1: Golden eval set methodology
- **Why matters:** eval set is load-bearing for detecting Risk 2. Named it as mitigation but don't know how to actually construct one.
- **How I'd close:** research eval-set methodology — how to sample queries from real traffic, how to get labels (SMEs vs LLM-as-judge), how many samples for statistical validity. Build a POC eval set on Lab 01's corpus first before doing it on real data.

### Gap 2: Cross-encoder reranker choice
- **Why matters:** reranker is the biggest quality-per-dollar lever in RAG; I proposed it in the design without knowing which specific model or what latency it adds.
- **How I'd close:** compare candidate models (`bge-reranker-large`, `cohere-rerank-v3`, sentence-transformers cross-encoders) on recall@5 lift, P99 latency, and cost per rerank. Deploy a POC that measures on realistic queries.

### Gap 3: End-to-end latency validation at 3s P99
- **Why matters:** committed to 3s P99 in the design without proving all pipeline stages fit inside it.
- **How I'd close:** load-test with realistic query distribution (200 sustained QPS + 5k burst). Instrument each stage (embed, search, ACL, rerank, LLM) with P99 latency histograms. Identify bottleneck stage and iterate.

### Coaching notes
- **Strong:** all three gaps are design-specific and honest — not throwaway modesty ("I don't know embeddings" would be silly given Week 1).
- **Sharpening needed:** name specific research *questions*, not just topics. "Understand rerankers" is a topic; "which reranker gives >5% recall@5 lift within 200ms P99 at $0.001/query?" is a research question.

---

## Self-Assessment After Case Study #1

| Skill | Before | After | Delta |
|-------|--------|-------|-------|
| SD self-rating | ~1.5/5 | ~2.5/5 | +1.0 |
| Framework fluency | reference-dependent | internalized shape | +1 |
| Diagram completeness | read path missing | both paths + ACL + auth | major |
| Trade-off structure | (skipped Week 1) | three-part shape locked in | major |
| Mechanism specificity | thin | thin (next muscle to build) | flat |

**Real biggest change:** Sections 5-7 (trade-offs, risks, gaps) — attempted for the first time. That's where interviews are decided. Ceiling raised.

**Next muscle to build:** mechanism specificity. Every mitigation and trade-off should name a specific technical thing (an algorithm, a data structure, a config value), not a category ("caching," "rerankers," "prompts").

---

## Meta-Lessons Locked In

1. **Ask for numbers upfront** using SNAP (Scale, Network, Availability, Purse).
2. **Every SD diagram closes three loops:** data in, query out, deletion/update.
3. **A trade-off has three parts:** what / gave-up / when-flips. Miss any and it's not a trade-off.
4. **A mitigation has a mechanism, not just an outcome.** "Prompt engineering" is an outcome; "post-generation grounding validator comparing answer claims to retrieved chunks" is a mechanism.
5. **Section 7 (what I don't know) signals seniority more than Sections 3-4 do.**
6. **The gap between "know it" and "can explain it" narrows only through timed reps under coaching.**
