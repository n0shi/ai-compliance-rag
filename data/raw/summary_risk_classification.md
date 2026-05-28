# AI Act Risk Classification Cheatsheet

**Source:** EU AI Act (Regulation 2024/1689) — own summary
**Last updated:** 2026-05-24

A compact decision-tree for classifying an AI system under the EU AI Act's four-tier
risk-based framework. Use this together with the full text of Articles 5, 6, 50, 51
and Annex III for authoritative reading.

---

## The four risk tiers

The AI Act follows a **risk-based approach** with four categories of AI systems.

### Tier 1 — Prohibited (Article 5)
AI practices presenting **unacceptable risk** to fundamental rights are banned outright.
Applicable from **2 February 2025**.

The eight prohibitions in Article 5(1):
- **(a)** Subliminal techniques beyond a person's consciousness that materially distort behaviour and cause significant harm.
- **(b)** Exploitation of vulnerabilities (age, disability, socio-economic situation) causing significant harm.
- **(c)** Social scoring by public authorities or on their behalf leading to detrimental treatment.
- **(d)** Risk assessment of natural persons to predict criminal offences based solely on profiling.
- **(e)** Untargeted scraping of facial images from the internet or CCTV to create facial recognition databases.
- **(f)** Inferring emotions in workplace or education contexts (except medical/safety reasons).
- **(g)** Biometric categorisation systems inferring race, political opinions, trade union membership, religious or philosophical beliefs, sex life, or sexual orientation.
- **(h)** Real-time remote biometric identification in publicly accessible spaces for law enforcement (with narrow exceptions in Article 5(2)–(7)).

**Penalty for breach:** up to EUR 35 million or 7% of global annual turnover (Article 99(3)).

### Tier 2 — High-risk (Article 6 + Annex III)
AI systems that may significantly impact safety or fundamental rights. Most obligations
apply from **2 August 2026** (Annex III); from **2 August 2027** for Annex I product safety.

An AI system is high-risk if **either**:
- **Article 6(1):** It is intended as a safety component of, or is itself, a product covered by Union harmonisation legislation listed in **Annex I** (e.g., medical devices, machinery, toys) AND that product requires third-party conformity assessment.
- **Article 6(2):** It falls within one of the use cases in **Annex III** (biometrics; critical infrastructure; education; employment; essential services; law enforcement; migration/asylum/border control; administration of justice; democratic processes).

**Article 6(3) carve-out** — a system listed in Annex III is **NOT** high-risk if it performs:
- (a) a **narrow procedural task**;
- (b) **improves the result** of a previously completed human activity;
- (c) detects **patterns / deviations** without replacing the human assessment without proper review;
- (d) is **preparatory** to an Annex III use case.
The carve-out does NOT apply if the system performs profiling of natural persons (Article 6(3) last sub-paragraph).

**Key obligations for providers of high-risk systems** (Chapter III, Section 2):
- Article 9 — risk management system
- Article 10 — data and data governance
- Article 11 — technical documentation (Annex IV)
- Article 12 — record-keeping (logging)
- Article 13 — transparency and information to deployers
- Article 14 — human oversight
- Article 15 — accuracy, robustness, cybersecurity
- Article 17 — quality management system
- Article 43 — conformity assessment
- Article 49 — registration in EU database

**Penalty for non-compliance:** up to EUR 15 million or 3% of global turnover (Article 99(4)).

### Tier 3 — Limited risk / Transparency (Article 50)
Specific AI systems with **transparency obligations** regardless of risk:
- **Article 50(1)** — providers must ensure systems interacting with natural persons disclose they are AI (unless obvious).
- **Article 50(2)** — providers of generative AI must mark outputs as artificially generated/manipulated in machine-readable form.
- **Article 50(3)** — deployers of emotion-recognition or biometric-categorisation systems must inform exposed persons.
- **Article 50(4)** — deployers of deepfakes must disclose the artificial nature; text published to inform the public on matters of public interest must be labelled as AI-generated (with exceptions).

### Tier 4 — Minimal risk
Everything else (spam filters, video game AI, inventory optimisation). **No mandatory obligations** under the AI Act. Voluntary codes of conduct (Article 95) encouraged.

---

## Decision flowchart

```
Question: Is your AI system regulated under the AI Act?
│
├─ Step 0: Is it an "AI system" per Article 3(1)?
│   (see Commission Guidelines on AI system definition, Feb 2025)
│   │
│   ├─ No → AI Act does not apply. Stop.
│   └─ Yes → continue.
│
├─ Step 1: Article 5 — Prohibited?
│   │
│   ├─ Yes (any of 8 categories) → CANNOT deploy. Stop.
│   └─ No → continue.
│
├─ Step 2: Article 6 — High-risk?
│   │
│   ├─ Annex I product safety (with 3rd-party CA)? OR
│   ├─ Annex III use case (and NOT covered by 6(3) carve-out)?
│   │   │
│   │   ├─ Yes → HIGH-RISK. Apply Chapter III obligations + conformity assessment.
│   │   └─ No → continue.
│   └─ Otherwise → continue.
│
├─ Step 3: Article 50 — Transparency?
│   │
│   ├─ Yes (chatbot, generative AI, emotion/biometric, deepfake) → apply transparency duties.
│   └─ No → continue.
│
└─ Step 4: MINIMAL risk. Voluntary codes only.
```

---

## GPAI carve-out (separate regime)

**General-purpose AI models** (Article 3(63)) have their own regime in Chapter V:
- All GPAI providers — obligations under Article 53 (technical documentation, copyright policy, training-data summary).
- **GPAI with systemic risk** (Article 51) — additional obligations under Article 55 (model evaluations, adversarial testing, serious incident reporting, cybersecurity).
- Presumption of systemic risk: cumulative training compute > **10^25 FLOPs** (Article 51(2)).

GPAI obligations apply from **2 August 2025**.

---

## Common misclassifications (and the correct answer)

| Scenario | Common wrong answer | Correct |
|---|---|---|
| Content moderation API for social media | "High-risk because Annex III" | NOT in Annex III; check DSA + Article 50 only |
| Emotion recognition in workplace wellness app | "High-risk" | **Prohibited** (Article 5(1)(f)) |
| LLM chatbot for customer support | "High-risk" | Limited (Article 50(1)) — must disclose it's AI |
| Generative image API used in adverts | "Minimal" | Limited (Article 50(2)) — outputs must be marked |
| HR resume-screening AI | "Minimal" | High-risk (Annex III §4 employment) |
| Fine-tuned open-source LLM for content moderation | "We're not GPAI" | If you fine-tuned a GPAI model, you may inherit GPAI obligations as a downstream provider (Article 25); if outputs are used in EU market, AI Act applies regardless of where the company is registered (Article 2(1)(c)) |

---

## Key cross-references

- AI system definition: Article 3(1); Commission Guidelines on AI system definition (29 Jul 2025).
- Prohibited practices: Article 5; Commission Guidelines on Prohibited Practices (4 Feb 2025).
- High-risk classification: Article 6; Annex III.
- Transparency: Article 50.
- GPAI: Articles 51–55.
- Penalties: Article 99.
- Timeline: Article 113.

---

## Authoritative caveat

This summary is for orientation only. The authoritative reading of the AI Act is given
by the Court of Justice of the EU. Engage qualified legal counsel before making
compliance decisions.
