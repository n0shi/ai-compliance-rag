# Content-Moderation AI — Compliance Checklist

**Sources:** EU AI Act (Reg. 2024/1689); DSA (Reg. 2022/2065); GDPR (Reg. 2016/679) — own summary
**Last updated:** 2026-05-24

This checklist targets ML startups building **AI-powered content-moderation systems**
(e.g., detection of sexism, hate speech, harassment, NSFW content) deployed via API
to social-media platforms, marketplaces, or end-user-facing services in the EU.

Use this checklist in tandem with the full text of cited Articles and competent legal
counsel. It is **not** legal advice.

---

## Step 0 — Scoping

Determine which regulations apply to **your** role:

| Your role | Applicable regimes |
|---|---|
| You build the moderation API and sell to platforms | **Provider** under AI Act (Art. 3(3)); possibly **processor** under GDPR; usually NOT directly a DSA subject. |
| You operate a social platform using your own moderation AI | **Provider AND deployer** (AI Act); **controller** (GDPR); **intermediary** under DSA. |
| You operate a platform using a third-party moderation tool | **Deployer** (AI Act Art. 3(4)); **controller** (GDPR); **intermediary** under DSA. |

**Article 25 AI Act warning:** if you substantially modify a high-risk AI system OR put your own brand on it, **you become the provider** with full provider obligations.

---

## Step 1 — AI Act classification of content moderation

### Is it an "AI system" (Article 3(1))?

Yes if it uses ML, deep learning, or logic/knowledge-based inference. Pure rule-based
filters (e.g., regex blocklist) may fall **outside** the definition (Commission
Guidelines on AI System Definition, Feb 2025, paragraphs 40–51).

### Is it prohibited (Article 5)?

For typical content moderation: **NO**, unless:
- [ ] Your system **infers emotions** of users in workplace/education context → Art. 5(1)(f) **prohibited**.
- [ ] Your system performs **biometric categorisation** inferring race, political opinions, religion, sex life, sexual orientation → Art. 5(1)(g) **prohibited**.
- [ ] Your system performs **social scoring** on behalf of a public authority → Art. 5(1)(c) **prohibited**.

### Is it high-risk (Article 6 + Annex III)?

For typical content moderation: **probably NO**. Annex III does not list general content
moderation. **However, edge cases:**

- [ ] Used in **law enforcement** context (e.g., flagging illegal content for police referral) → Annex III §6 high-risk.
- [ ] Used to **filter applications** in employment/education contexts → Annex III §4 / §3 high-risk.
- [ ] Acts as **safety component** of regulated product (e.g., children's device) → Article 6(1) high-risk.

Most pure social-media moderation will not trigger Annex III. **Document your classification reasoning** even when concluding not high-risk (Art. 6(4)).

### Article 50 transparency obligations

- [ ] If your moderation outputs labels visible to users ("this comment violates X") → Art. 50(1) **disclose interaction with AI** (unless obvious from context).
- [ ] If your system generates **synthetic moderation responses** (e.g., AI explanation text) → Art. 50(2) **mark as AI-generated** in machine-readable form.
- [ ] If your system detects deepfakes among uploaded content → no direct Art. 50(4) obligation on you (that's on the deployer), but consider transparency to your customer.

---

## Step 2 — GDPR obligations (always relevant)

Content moderation almost always processes personal data (usernames, post content
identifying authors, behavioural signals).

- [ ] Identify your role: **controller** (you decide why and how) vs **processor** (you act on instructions of the platform).
- [ ] Lawful basis (Art. 6): typically Art. 6(1)(f) **legitimate interest** of the platform; document **three-step assessment** (EDPB Opinion 28/2024 reaffirms requirements).
- [ ] **Special-category data** (Art. 9): if your moderation infers religion/politics/sexual orientation of users — Art. 9(2) lawful basis required. **High bar.**
- [ ] **Article 22 — automated decisions:** if moderation alone causes legal or significantly affects user (account suspension, monetization removal) → user has right to obtain **human intervention** and contest. Build the human-review pipeline.
- [ ] **DPIA (Art. 35):** required for systematic large-scale moderation → conduct and update.
- [ ] **Information to data subjects (Art. 13/14):** moderation purpose and logic must be in the privacy notice. Note "meaningful information about the logic involved" requirement.
- [ ] **Data minimisation (Art. 5(1)(c)):** train and operate on the minimum personal data needed.
- [ ] **Storage limitation (Art. 5(1)(e)):** retain training data only as long as necessary; document retention schedule.

---

## Step 3 — DSA obligations (only if your customer is a platform)

DSA applies to **intermediary services** offered to users in the EU. The provider of
the moderation AI is usually NOT a direct DSA subject, but the **platform deploying
the AI is** — and they will push obligations down via contract.

| DSA provision | What the platform must do | What you must enable |
|---|---|---|
| Article 14 — terms & conditions | Disclose moderation policies, including AI-driven mechanisms | Document your detection categories so the platform can describe them. |
| Article 17 — statement of reasons | Provide users with reasons for every content moderation decision (removal, demotion, account restriction) | Output explanations / category labels per decision. |
| Article 20 — internal complaint-handling | Free, user-friendly mechanism to challenge decisions | Keep raw signals reproducible for re-review. |
| Article 21 — out-of-court dispute settlement | Submit to certified ODR bodies | Cooperate; preserve evidence. |
| Article 23 — measures against misuse | Suspend repeat offenders | Provide reliable user-level scoring. |
| Article 27 — recommender system transparency | Explain main parameters of recommender systems (if applicable) | If moderation feeds into ranking/recommendation, prepare parameter documentation. |
| Article 34 (VLOPs only) — systemic risk assessment | Annual risk assessment incl. systemic risk from automated content moderation | Provide audit-ready evidence (accuracy, false-positive rates, demographic disparities). |

If the platform is a **VLOP (Very Large Online Platform)** designated under DSA Art. 33,
the AI moderation tool becomes a focus of EU Commission scrutiny.

---

## Step 4 — Sector-specific overlays (do they apply to you?)

- [ ] **Children's services** → CoPPA-equivalent (Art. 28 DSA), AI Act Recital 48 child safety.
- [ ] **Hosting in regulated industries** (finance, health, government) → sectoral rules + AI Act high-risk if applicable.
- [ ] **Audiovisual services** → AVMS Directive content rules + DSA.

---

## Step 5 — Documentation pack (assemble these before deployment)

Even if your system is NOT high-risk, having the following protects you in audits and
in regulator inquiries:

1. **AI system definition assessment** — why your system is/isn't an "AI system" per Art. 3(1).
2. **Risk classification memo** — Art. 5/6/50 analysis with citations.
3. **Article 6(3) carve-out justification** (if applicable).
4. **Joint DPIA + FRIA** — combined GDPR + AI Act fundamental-rights impact analysis.
5. **Technical documentation** — model card, training data summary (Art. 53 if GPAI-derived), evaluation results, monitoring metrics.
6. **Bias and accuracy report** — false-positive/false-negative rates per relevant demographic group.
7. **Data lineage** — source, lawful basis, retention for every dataset.
8. **Human oversight design** — who reviews; SLA for human review; appeal flow.
9. **Incident response plan** — Art. 73 AI Act serious-incident reporting (high-risk only); Art. 33 GDPR breach notice.
10. **Penalty exposure analysis** — estimate worst-case fines (AI Act Art. 99 + GDPR Art. 83) for each non-compliance scenario.

---

## Step 6 — Timeline awareness

| Date | Obligation triggers |
|---|---|
| **2 Feb 2025** | Art. 5 prohibitions; Art. 4 AI literacy. **Already in force.** |
| **2 Aug 2025** | GPAI obligations (if you use foundation models); AI Office governance. |
| **2 Aug 2026** | Most high-risk obligations (Annex III). |
| **2 Aug 2027** | High-risk for Annex I product safety systems. |

---

## Quick test: am I likely high-risk?

Answer YES/NO:

- Does the system make decisions in **law enforcement, migration, justice, or democratic processes**? [ ]
- Does the system **filter humans** in employment, education, or access to essential services? [ ]
- Is the system a **safety component** of a regulated product (medical, automotive, toy)? [ ]
- Does the system perform **biometric identification or categorisation**? [ ]

**Two or more YES** — likely high-risk. Get specific legal advice before deploying.
**All NO** — likely not Annex III high-risk. Still verify Art. 5 prohibitions and Art. 50 transparency.

---

## Authoritative caveat

This checklist is for orientation only. Apply with qualified legal counsel; the
classifications above are typical, not universal. Penalties are substantial: up to
EUR 35M / 7% global turnover for prohibited practices (AI Act Art. 99(3)) and up to
EUR 20M / 4% under GDPR (Art. 83(5)).
