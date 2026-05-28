# AI Act × GDPR Overlap Matrix

**Sources:** EU AI Act (Reg. 2024/1689); GDPR (Reg. 2016/679); EDPB Opinion 28/2024 — own summary
**Last updated:** 2026-05-24

The AI Act and GDPR apply **in parallel and cumulatively**. An AI provider or deployer
processing personal data must satisfy both regimes. This document maps the most
operationally relevant overlaps and identifies where the two laws diverge.

---

## Foundational principle: lex specialis or cumulative?

Recital 9 AI Act clarifies that the AI Act **does not affect the application of GDPR**.
The two regimes are cumulative: AI Act addresses product-safety-style obligations on the
**system**; GDPR addresses obligations on the **processing of personal data**.

EDPB Opinion 28/2024 confirms that compliance with the AI Act does not exempt
processing operations from GDPR scrutiny by supervisory authorities.

---

## Mapping table

| AI Act provision | Related GDPR provision | Operational note |
|---|---|---|
| Article 3(1) — definition of "AI system" | — | No GDPR equivalent. Determines whether AI Act applies at all. |
| Article 4 — AI literacy | Article 39 — DPO tasks | DPO training overlaps with AI literacy obligations for staff processing personal data. |
| Article 5 — prohibited practices | Article 9 — special categories; Article 22 — ADM | Many Article 5 prohibitions also process special-category data (e.g., biometric categorisation infers Article 9 attributes). GDPR Article 9 prohibition + AI Act Article 5 prohibition stack. |
| Article 5(1)(f) — emotion recognition in workplace | Article 9 — special categories (potentially); Article 88 — employment context | Workplace context triggers both. |
| Article 9 — risk management system | Article 35 — DPIA; Article 25 — data protection by design | AI Act RMS and GDPR DPIA are **distinct documents** but evidence overlaps; conduct in parallel. |
| Article 10 — data and data governance (high-risk) | Article 5(1) principles; Article 6 — lawful basis; Article 9 — special categories | Article 10(5) explicitly permits processing of special-category data for bias correction in high-risk systems — but only subject to safeguards. |
| Article 12 — record-keeping (logging) | Article 30 — records of processing | Logs may contain personal data → GDPR record-keeping applies on top. |
| Article 13 — transparency to deployers | Article 13/14 — information to data subjects | AI Act Article 13 is **provider → deployer**; GDPR Articles 13/14 are **controller → data subject**. Different audience. |
| Article 14 — human oversight (high-risk) | Article 22 — automated individual decisions | Article 14 ensures human can override the system; Article 22 gives the **data subject** the right to obtain human intervention. Different mechanism, complementary aim. |
| Article 26 — deployer obligations | Article 24 — controller responsibility | Deployer ≈ controller in many cases; deployer's FRIA (Article 27) complements DPIA. |
| Article 27 — fundamental rights impact assessment (FRIA) | Article 35 — DPIA | FRIA covers fundamental rights beyond data protection. EDPB recommends a **combined assessment** in practice. |
| Article 50(1) — disclose interaction with AI | Article 13/14 — inform data subjects | If chatbot collects personal data, BOTH disclosures required (different content). |
| Article 50(3) — inform persons subject to emotion/biometric AI | Article 13/14 + Article 9 lawful basis | Triple overlap: AI Act notice + GDPR notice + lawful basis under Article 9(2). |
| Article 60 — testing in real-world conditions | Article 6(1)(a) — consent; Recital 161 AI Act | Real-world testing typically requires informed consent. |
| Article 99 — penalties (AI Act) | Article 83 — fines (GDPR) | Penalties can **stack** for the same factual matter when different obligations are breached. |

---

## Article 22 GDPR × Article 14 AI Act: the most-asked overlap

| Aspect | GDPR Art. 22 | AI Act Art. 14 |
|---|---|---|
| Who is protected? | The **data subject** (individual). | The **affected persons** generally; primary aim is system safety. |
| What is the right? | Right NOT to be subject to solely automated decisions with legal/significant effects. | System must be **designed** so a competent natural person can oversee it. |
| Trigger | Decision is **solely automated** AND has legal/significant effect on the individual. | System is **high-risk** (Article 6). |
| Remedy | Data subject can request human intervention, express view, contest decision. | Provider must build in overseer interface; deployer must assign trained personnel. |
| Penalty | Up to 4% global turnover (GDPR Art. 83(5)). | Up to 3% (Art. 99(4)) for breach. |
| Personal data required? | YES — GDPR only applies to personal data. | NO — AI Act applies to AI systems regardless. |

A content-moderation system that auto-deletes user posts may trigger BOTH:
- Art. 22 (if the user has legal or significant effect, e.g. account suspension), and
- Art. 14 (if the system is otherwise classified as high-risk).

---

## EDPB Opinion 28/2024 — key points relevant to overlap

EDPB Opinion 28/2024 (17 Dec 2024) addresses how GDPR applies to AI models:

1. **Anonymity of trained models:** Determined case-by-case. The likelihood of extracting personal data via probabilistic methods must be "insignificant" for a model to be considered anonymous.
2. **Legitimate interest (Art. 6(1)(f) GDPR):** Three-step assessment required (purpose; necessity; balancing). Particularly relevant for training data scraped from the web.
3. **Unlawful processing in training phase:** May taint subsequent processing in the deployment phase, depending on circumstances.
4. **Development vs deployment phases:** EDPB distinguishes these as separate processing activities, each requiring its own GDPR analysis.

This opinion is the most important bridge document between AI Act and GDPR.

---

## Practical advice for content-moderation startup

Joint AI Act + GDPR checklist:
- [ ] Map every personal-data flow in your AI system (GDPR Art. 30).
- [ ] If outputs trigger user-account consequences → assess Art. 22 GDPR + Art. 50 AI Act.
- [ ] Combine DPIA (GDPR Art. 35) with FRIA (AI Act Art. 27) into a single document if your system is both high-risk and processes personal data.
- [ ] Verify lawful basis for training data — esp. if scraped (EDPB Opinion 28/2024).
- [ ] Document each safeguard as evidence for both regulators.

---

## Authoritative caveat

The relationship between AI Act and GDPR is unsettled in places; case law from CJEU and
EDPB-EU AI Office coordination will shape practice through 2026-2027. Do not rely on
this summary alone for compliance decisions; consult qualified counsel.
