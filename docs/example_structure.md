# Orqestra Seed Dataset Engineering Guide (2026 Blueprint)

To make the Orqestra 50-seed dataset highly effective, you cannot simply feed the compiler random sentences.

Because DSPy uses these examples to dynamically generate few-shot prompts and teach GPT-4o-mini your exact definition of logic, these 50 examples must be engineered like a pristine scientific calibration set.

If your seed dataset contains ambiguous examples, the compiled model's accuracy will collapse.

To guarantee the highest-quality examples for this task, your 50-row dataset must adhere to:

- A strict distribution matrix
- Clear grammatical structure rules
- Explicit logical boundary definitions

---

# 1. The Balance Matrix (2026 Blueprint)

A common mistake is creating a dataset with 40 contradictions and 10 neutrals.

If you do this, the model develops a **pessimistic bias** and begins predicting `Contradiction` for nearly everything.

Your 50 examples should follow this distribution:

| Domain | Contradictions | Neutrals | Entailments | Total |
|----------|----------|----------|----------|----------|
| Healthcare (Primary) | 7 | 7 | 3 | 17 |
| Finance (Secondary) | 5 | 5 | 2 | 12 |
| Legal / Compliance | 3 | 3 | 1 | 7 |
| HR / Corporate Policy | 3 | 3 | 1 | 7 |
| DevOps / Cybersecurity | 3 | 3 | 1 | 7 |
| **TOTALS** | **21** | **21** | **8** | **50** |

> **Note:** Contradictions and Neutrals receive significantly higher weight because they represent the hardest logical boundary for LLMs to distinguish.

---

# 2. The Four Structural Pillars of a Perfect Example

Every example added to `orqestra_50.py` should satisfy all four criteria.

## 2.1 Entity Consistency

Both Claim A and Claim B must focus on the exact same core subject.

### Good

- Both claims discuss Metformin
- Both claims discuss AWS S3 Buckets
- Both claims discuss Maternity Leave

### Bad

- Claim A discusses Metformin
- Claim B discusses Insulin

Different entities teach the model nothing because the relationship becomes trivially Neutral.

---

## 2.2 Contextual Intersection

The claims must overlap in at least one of:

- Time
- Scope
- Geography
- Policy jurisdiction
- Operational context

Without contextual overlap, there is no meaningful logical comparison.

---

## 2.3 Conversational Stripping

Remove conversational framing.

### Avoid

```text
According to our system...
We recommend...
As an AI...
Our platform believes...
```

### Prefer

```text
All active deployments require two peer reviews.
```

Claims should be written as direct factual assertions.

---

## 2.4 Explicit Values

Use:

- Exact numbers
- Defined ranges
- Absolute states

### Avoid

```text
High risk
Low confidence
Large discount
```

### Prefer

```text
Risk score exceeds 0.85
Discount equals 15%
Confidence threshold is 90%
```

---

# 3. Class-by-Class Recipe Guide

---

# Contradiction (21 Examples)

A contradiction exists when Claim A and Claim B cannot simultaneously be true under the same conditions.

## Formula

Condition X is true.

- Claim A mandates Action Y.
- Claim B forbids Action Y.

Or:

- Claim B mandates Action Z.
- Action Z makes Action Y impossible.

---

## Weak Contradiction

### Claim A

```text
The price is $10.
```

### Claim B

```text
The price is $20.
```

This is too easy.

Simple pattern matching can detect it.

---

## High-Quality Contradiction

### Claim A

```text
All active code deployments require a minimum of two senior peer reviews prior to merging.
```

### Claim B

```text
Hotfix patches targeting critical infrastructure can bypass senior approval loops and merge automatically with one junior sign-off.
```

### Why It Works

This example creates a subtle procedural collision instead of a superficial numeric mismatch.

---

# Neutral (21 Examples)

For Orqestra, Neutral should primarily represent:

**General Rule vs. Specific Exception**

This is one of the most difficult logical distinctions for LLMs.

The model must learn:

> These claims appear conflicting, but actually coexist safely.

---

## Formula

### Claim A

A broad policy.

### Claim B

A narrow exception that applies only under a specific condition.

---

## Key Signal

Claim B should include an explicit trigger such as:

```text
If
Unless
Except when
Only when
In cases where
Provided that
```

---

## High-Quality Neutral

### Claim A

```text
Standard maternity leave provides 12 weeks of fully compensated time off for all full-time corporate staff.
```

### Claim B

```text
Employees operating under localized European manufacturing union contracts are granted 24 weeks of parental leave.
```

### Why It Works

A weak model sees:

```text
12 weeks
24 weeks
```

and predicts contradiction.

A stronger model recognizes the exception boundary:

```text
European manufacturing union contracts
```

and classifies the pair as Neutral.

---

# Entailment (8 Examples)

An entailment exists when Claim B is guaranteed to be true if Claim A is true.

---

## Formula

Claim B is:

- A semantic paraphrase of Claim A
- A mathematically equivalent statement
- A broader statement that fully contains Claim A

---

## High-Quality Entailment

### Claim A

```text
The platform charges a flat processing fee of 150 basis points on all cross-border wire transfers.
```

### Claim B

```text
International wire transfers incur a transactional fee of 1.5%.
```

### Why It Works

The model must recognize:

```text
150 basis points = 1.5%
```

This tests semantic and mathematical alignment simultaneously.

---

# 4. Quality Checklist Before Compilation

Before adding any example to the seed dataset, verify:

- [ ] The example avoids referencing proprietary system names (e.g., HealthTrack).
- [ ] Labels are exactly:
  - `Contradiction`
  - `Neutral`
  - `Entailment`
- [ ] No Neutral example is actually a hidden contradiction.
- [ ] A domain expert (lawyer, doctor, compliance officer, engineer) would immediately agree with the assigned label.
- [ ] Entity consistency is preserved.
- [ ] Contextual overlap exists.
- [ ] Claims are written as factual assertions.
- [ ] Explicit values are used wherever possible.

---

# Objective

The purpose of the seed dataset is not merely to provide examples.

It is to create a high-fidelity logical calibration set that teaches the compiler the precise distinction between:

- True contradictions
- Safe exceptions
- Semantic equivalence

A well-engineered 50-example dataset will significantly outperform a much larger but noisier dataset because the compiler learns logical boundaries rather than surface patterns.‰