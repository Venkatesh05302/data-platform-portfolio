# Clarifying Questions — Cheat Sheet

Sub-framework for Step 1 of the SD interview framework. When the interviewer says *"design X,"* you have ~5 minutes to ask enough questions that the rest of the design has direction. This sheet is what to ask, in what order, using what mental model.

Pair with: [`00_framework.md`](./00_framework.md) (the parent 6-step framework).

---

## The Buckets — Ask 2-3 In Each

Never skip a bucket. Aim for 10-12 total questions in ~5 min.

| Bucket | What you're probing | Example |
|--------|---------------------|---------|
| **1. Functional (what)** | What does the system DO? | "What does a result look like?" |
| **2. Non-functional (how well)** | Scale, latency, availability | "Peak QPS? P99 latency?" |
| **3. Users (who)** | Who uses it, when, how | "How many concurrent users at peak?" |
| **4. Constraints (bounds)** | Budget, timeline, existing infra | "Greenfield or extending?" |
| **5. Unique (this problem)** | What makes THIS problem hard | "How do access controls work?" |

---

## SNAP — The Four Numbers, Ask First

Every SD problem needs four numbers upfront. Ninety seconds, four questions. Everything downstream flows from these:

- **S**cale — QPS, users, data volume
- **N**etwork — latency target, freshness SLA
- **A**vailability — 9s target, cost of downtime
- **P**urse — budget envelope

Ask SNAP first. Then move to the buckets.

---

## The Two Muscles Behind Good Questions

### Muscle 1 — "What decision does this unblock?"

Before asking, ask yourself: *"if the sponsor answers X vs Y, does my design change?"* If no, don't ask.

- ❌ Bad: *"What's your favorite database?"* — sponsor preference doesn't drive design
- ✅ Good: *"Freshness SLA — 5 min or 1 hour?"* — 5 min forces streaming; 1 hour allows batch

### Muscle 2 — "Numbers, not adjectives"

Force each question to return a **number, boolean, or specific noun** — never an adjective.

- ❌ Bad: *"Is it high-throughput?"* → sponsor says "yes." You learned nothing.
- ✅ Good: *"5k QPS or 50k QPS at peak?"* → actionable answer.

---

## The 5-Minute Structure

```
0:00 - 0:30   SNAP — 4 questions for the 4 numbers
0:30 - 1:30   FUNCTIONAL — 2-3 questions on what the system does
1:30 - 2:30   USERS — 2-3 questions on who uses it and how
2:30 - 4:00   UNIQUE — 2-3 questions on what makes THIS problem hard
4:00 - 5:00   Confirm scope back to interviewer, get a nod, move on
```

Then start Step 2 (Capacity Estimation) with numbers in hand.

---

## The Cheat Card (Print This)

```
┌──────────────────────────────────────────────────────────────────┐
│ CLARIFYING QUESTIONS CHEAT CARD                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SNAP (numbers, ask first):                                      │
│    • Scale? (QPS, users, data volume)                            │
│    • Network? (P99 latency, freshness SLA)                       │
│    • Availability? (9s target)                                   │
│    • Purse? (budget)                                             │
│                                                                  │
│  FUNCTIONAL (what):                                              │
│    • What does a "result" look like?                             │
│    • What's out of scope?                                        │
│    • Single-user or multi-tenant?                                │
│                                                                  │
│  USERS (who):                                                    │
│    • How many concurrent users at peak?                          │
│    • What triggers a user to use this? (usage pattern)           │
│                                                                  │
│  UNIQUE (this problem):                                          │
│    • What's the hardest constraint?                              │
│    • Any existing infra we're leveraging or replacing?           │
│    • Compliance / security specifics?                            │
│                                                                  │
│  RULE: every question returns a NUMBER, BOOLEAN, or NOUN.        │
│        Never an adjective.                                       │
│        If sponsor's answer doesn't change your design, cut it.   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Traps To Avoid

1. **Question stubs instead of questions** — writing "ACLs" is not a question. *"How do access controls work today — central identity service or per-source?"* is a question.
2. **Guessing architecture in question form** — *"Should we use vectors?"* is you deciding the design, not asking about the problem.
3. **Yes/no questions on adjectives** — *"Is it critical?"* gets a "yes." Ask *"Any downtime tolerated during business hours, or 24/7 hot?"* instead.
4. **Asking preferences** — sponsor preference is not requirements. Ask about *the world*, not *what they want*.
5. **Skipping SNAP because it feels basic** — the four numbers are exactly what a senior candidate probes first. Skipping them signals inexperience.

---

## Practice Without An SD Prompt

You can drill this muscle without a formal exercise. Pick 3 systems you know:

- Systems at your current job
- Apps you use daily (Slack, Uber Eats, GitHub, your bank app)

For each, generate **10 clarifying questions using this framework**. 3 systems × 10 questions = 30 reps in an hour. Do this once a week for a month and the framework becomes automatic.

**Constraint for the practice:** every question must return a number, boolean, or specific noun. If you catch yourself asking an adjective question, rewrite it.

---

## Worked Example — "Design a document search system"

```
SNAP:
1. Peak QPS during business hours vs. off-hours — sustained or burst?
2. Answer P99 latency target — sub-second, 1s, 3s?
3. Availability target — internal tool (99%) or user-facing (99.9%+)?
4. Budget envelope — $10k/month, $100k/month, $1M/month?

Functional:
5. What does a "result" look like — list of docs, or synthesized answer with citations?
6. Do we search within docs (line-level), at doc level, or both?
7. Any content types out of scope (audio, video, code)?

Users:
8. How many concurrent users at peak? Total employee count is a ceiling.
9. What triggers a search — daily habit, occasional lookup, "I'm stuck" moment?

Unique to this problem:
10. Access controls — mirror per-source, or central identity service?
11. What happens on document deletion — must search reflect immediately?
12. Any existing search stack we're replacing or supplementing?
```

Twelve questions. ~5 minutes. Every answer changes the design.
