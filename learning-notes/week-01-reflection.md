# Week 1 Reflection

**Week of:** 2026-06-30 (completed over ~5 weeks at self-directed pace)
**Baseline ratings:** Spark 3/5 · SQL 4/5 · System Design 1/5 · AI/LLM 1/5

---

## What surprised me about embeddings?

The Word2Vec training approach. The idea that a model learns word meaning not from labels or definitions, but from *what other words the word appears next to* — the distributional hypothesis — was counter-intuitive. I hadn't seen the "predict the neighbors, throw away the prediction, keep the hidden layer" trick before. That the meaning of "king" and "queen" emerges as a *direction* in vector space (rather than being explicitly encoded anywhere) is not something I would have designed on my own.

## What's still fuzzy?

**Evaluation.** I built a retrieval system in Lab 01 and captured recall@k / MRR numbers, but I still don't have strong intuition for what "good enough" looks like on a real production system — how to design an eval set from scratch for a new domain, when to trust vector-only metrics vs. user-facing metrics like click-through, and how to detect that retrieval has silently degraded over time.

## What did the system design exercise feel like?

Uncomfortable in the middle, but it worked — I'm more interested in system design than I expected to be. The specificity gap between my answers and the coached "would-score-well" versions was clear and useful. It made me want to do more of these, not fewer.

## One question I want answered next week

**If Word2Vec is obsolete, what are today's leading embedding approaches, and why does the Word2Vec intuition still hold?** Specifically: what changed between Word2Vec and modern transformer-based sentence encoders (MiniLM, MPNet, OpenAI text-embedding-3) — and what stayed the same at the mental-model level? Understanding what carries forward and what got replaced would help me reason about the *next* generation of embeddings when they arrive.

---

## Self-assessment update after Week 1

| Skill | Baseline | After Week 1 | Notes |
|-------|----------|--------------|-------|
| AI/LLM | 1/5 | ~2.5/5 | Real progress — embeddings theory + working retrieval lab + drift/migration DE angle |
| System Design | 1/5 | ~1.5/5 | Framework internalized; first exercise attempted; needs many more reps |
| Spark | 3/5 | 3/5 | Not touched this week (intentional) |
| SQL | 4/5 | 4/5 | Not touched this week (intentional) |

Real biggest change: I now believe SD is trainable and I'm willing to do the reps. That mindset shift may matter more than any specific concept learned.
