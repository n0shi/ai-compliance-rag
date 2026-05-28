# Glossary of AI Act Terms

**Source:** EU AI Act (Regulation 2024/1689), GDPR (Regulation 2016/679), DSA (Regulation 2022/2065) — own summary
**Last updated:** 2026-05-24

Compact reference for the most-frequently-confused terms in EU AI compliance.
Each entry cites the source Article. For authoritative interpretation, consult the
full legal text and qualified counsel.

---

## Core definitions (Article 3 AI Act unless noted)

**AI system** — Art. 3(1)
A machine-based system designed to operate with varying levels of autonomy, that may
exhibit adaptiveness after deployment, and that, for explicit or implicit objectives,
infers from input how to generate outputs (predictions, content, recommendations,
decisions) that can influence physical or virtual environments.
*The Commission Guidelines on AI System Definition (Feb 2025) identify seven elements
of this definition. Pure rule-based systems with no learning/inference fall outside.*

**Risk** — Art. 3(2)
The combination of the probability of harm occurring and its severity.

**Provider** — Art. 3(3)
A natural or legal person, public authority, agency, or other body that **develops**
an AI system or general-purpose AI model and places it on the market or puts it into
service under its own name or trademark, whether for payment or free of charge.

**Deployer** — Art. 3(4)
A natural or legal person using an AI system under its authority, except where used
in a personal non-professional activity.
*Old drafts called this "user"; final text uses "deployer".*

**Authorised representative** — Art. 3(5)
EU-based natural or legal person mandated in writing by a non-EU provider to perform
provider obligations under the AI Act on its behalf.

**Importer** — Art. 3(6)
Natural or legal person established in the EU that places on the market an AI system
bearing the name/trademark of a person established outside the EU.

**Distributor** — Art. 3(7)
Natural or legal person in the supply chain, other than provider or importer, that
makes an AI system available on the EU market.

**Operator** — Art. 3(8)
Umbrella term: provider, product manufacturer, deployer, authorised representative,
importer, or distributor.

**Placing on the market** — Art. 3(9)
First making available of an AI system or GPAI model on the EU market.

**Making available on the market** — Art. 3(10)
Any supply for distribution or use in the EU market in the course of commercial activity.

**Putting into service** — Art. 3(11)
Supply of an AI system to the deployer for first use directly, OR for own use in the
EU for its intended purpose.

**Intended purpose** — Art. 3(12)
Use for which an AI system is intended by the provider, including specific context and
conditions of use as specified in the instructions for use, promotional materials, and
technical documentation.

**Reasonably foreseeable misuse** — Art. 3(13)
Use in a way not aligned with the intended purpose but which may result from
**reasonably foreseeable human behaviour** or interaction with other systems.

**Safety component** — Art. 3(14)
Component of a product or AI system that performs a safety function or whose failure
endangers health, safety, property, or the environment.

**Substantial modification** — Art. 3(23)
Change to an AI system after placing on market that **was not foreseen** in the initial
conformity assessment AND affects compliance with Chapter III Section 2, OR results in
modification of intended purpose.
*A deployer who substantially modifies a high-risk system steps into provider role under Art. 25.*

---

## Risk-tier terms

**Prohibited AI practices** — Art. 5
Eight categories of AI uses presenting **unacceptable risk** to fundamental rights.
Banned outright from 2 Feb 2025. Fine: up to EUR 35M or 7% global turnover.

**High-risk AI system** — Art. 6
AI system that EITHER acts as a safety component of an Annex I regulated product
requiring third-party CA, OR falls within Annex III use cases. Subject to Chapter III
Section 2 obligations. Fine for non-compliance: up to EUR 15M or 3%.

**Annex I** (referenced by Art. 6(1))
List of EU harmonisation legislation (machinery, medical devices, toys, etc.) under
which AI systems acting as safety components are automatically high-risk.

**Annex III** (referenced by Art. 6(2))
List of eight high-risk use cases: (1) biometrics, (2) critical infrastructure,
(3) education and vocational training, (4) employment, (5) essential private and
public services, (6) law enforcement, (7) migration/asylum/border control,
(8) administration of justice and democratic processes.

**Article 6(3) carve-out**
An Annex III system is NOT high-risk if it performs only a narrow procedural task,
improves a prior human result, detects patterns/deviations (not replacing human review),
or is preparatory. Does NOT apply if profiling natural persons.

**Limited-risk system / transparency obligation** — Art. 50
AI systems interacting with humans, generative AI outputs, emotion/biometric
categorisation, deepfakes. Specific transparency duties on provider and/or deployer.

**Minimal-risk system**
Everything not prohibited, high-risk, or subject to Art. 50. No mandatory obligations;
voluntary codes of conduct (Art. 95) encouraged.

---

## GPAI terms (Chapter V)

**General-purpose AI model (GPAI)** — Art. 3(63)
An AI model, including one trained with self-supervision at scale, that displays
**significant generality** and is capable of competently performing a wide range of
distinct tasks; can be integrated into a variety of downstream systems or applications.
Excludes models for research/development before placing on the market.

**GPAI model with systemic risk** — Art. 51
GPAI presenting capabilities matching or exceeding the most advanced models, OR
designated as such by the Commission. **Presumption:** cumulative training compute >
10^25 FLOPs.

**GPAI system** — Art. 3(66)
AI system based on a GPAI model that can serve a variety of purposes.

**Code of Practice for GPAI** — Art. 56
Voluntary instrument adopted by the AI Office providing means to comply with GPAI
provider obligations under Arts. 53 and 55. Published 10 July 2025.

---

## Governance terms

**AI Office** — Art. 64
EU body established within the European Commission to oversee implementation of the
AI Act, particularly for GPAI models. Operational from 2 Aug 2025.

**European Artificial Intelligence Board** — Art. 65
Board of Member State representatives advising the Commission on AI Act implementation.

**Scientific Panel of independent experts** — Art. 68
Supports AI Office, in particular for GPAI model assessment.

**National competent authority** — Art. 70
Member State authority designated to apply and enforce the AI Act. No "one-stop-shop"
mechanism like GDPR — companies may face multiple national authorities.

**Notified body** — Art. 3(22) and Chapter IV
Conformity assessment body designated by a Member State to perform third-party
conformity assessment of high-risk AI systems.

**Conformity assessment** — Art. 3(20), Arts. 43–47
Process of verifying that a high-risk AI system meets the requirements of Chapter III
Section 2. Can be internal (Annex VI) or with notified body (Annex VII).

**Declaration of conformity** — Art. 47 + Annex V
Signed declaration by provider that high-risk AI system meets all applicable requirements.

**CE marking** — Art. 48
Visible/digital marking indicating conformity of high-risk AI system.

---

## Process terms

**Risk management system (RMS)** — Art. 9
Iterative process throughout the AI system lifecycle to identify, evaluate, and
mitigate risks. Required for high-risk systems.

**Quality management system (QMS)** — Art. 17
Documented system covering compliance strategies, design, development, post-market
monitoring. Required for high-risk providers.

**Technical documentation** — Art. 11 + Annex IV
Documentation enabling assessment of conformity. Annex IV specifies minimum contents.
Simplified form available for SMEs and start-ups.

**Fundamental Rights Impact Assessment (FRIA)** — Art. 27
Assessment that deployers of certain high-risk AI systems must perform before deployment,
documenting impacts on fundamental rights. Complements (does not replace) GDPR DPIA.

**Post-market monitoring system** — Art. 72
System for collecting and analysing data on AI system performance after deployment.

**Serious incident** — Art. 3(49), Art. 73
Incident or malfunction leading to: death, serious harm to health, serious and
irreversible disruption of critical infrastructure, breach of fundamental rights, or
serious harm to property/environment. Must be reported within specified timeframes.

---

## GDPR cross-reference terms (Reg. 2016/679)

**Personal data** — GDPR Art. 4(1)
Any information relating to an identified or identifiable natural person.

**Controller** — GDPR Art. 4(7)
Person/body that determines the purposes and means of the processing of personal data.

**Processor** — GDPR Art. 4(8)
Person/body that processes personal data on behalf of the controller.

**Special categories** — GDPR Art. 9
Racial/ethnic origin, political opinions, religious or philosophical beliefs, trade-union
membership, genetic data, biometric data for identification, health, sex life, sexual orientation.

**Automated individual decision-making (ADM)** — GDPR Art. 22
Decisions based solely on automated processing producing legal effects or similarly
significantly affecting the data subject. Subject to specific safeguards including the
right to human intervention.

**Data Protection Impact Assessment (DPIA)** — GDPR Art. 35
Assessment of risks of processing operations to rights and freedoms of natural persons.
Required for high-risk processing. Separate from but related to AI Act FRIA.

---

## DSA cross-reference terms (Reg. 2022/2065)

**Intermediary service** — DSA Art. 3(g)
Service of mere conduit, caching, or hosting.

**Hosting service** — DSA Art. 3(g)(iii)
Service that stores information at request of recipient.

**Online platform** — DSA Art. 3(i)
Hosting service that, at the request of a recipient, stores and disseminates information
to the public.

**Very Large Online Platform (VLOP) / VLOSE** — DSA Art. 33
Platform/search engine with > 45 million average monthly active users in the EU. Subject
to stricter obligations (Arts. 34–43).

**Statement of reasons** — DSA Art. 17
Clear and specific statement that platforms must provide to users for every content
moderation decision.

**Trusted flagger** — DSA Art. 22
Entity certified by Member State Digital Services Coordinator to flag illegal content.

---

## Penalty quick reference

| Regime | Maximum fine |
|---|---|
| AI Act Art. 5 (prohibited practices) | EUR 35M or 7% global annual turnover, whichever higher (Art. 99(3)) |
| AI Act other obligations | EUR 15M or 3% (Art. 99(4)) |
| AI Act incorrect information to authorities | EUR 7.5M or 1% (Art. 99(5)) |
| GDPR most serious | EUR 20M or 4% (Art. 83(5)) |
| GDPR other | EUR 10M or 2% (Art. 83(4)) |
| DSA most serious | 6% of global annual turnover (Art. 74) |

For SMEs and start-ups, AI Act Art. 99(6) applies the **lower** of the two amounts.

---

## Authoritative caveat

Definitions evolve with Commission Guidelines, EDPB opinions, AI Office decisions, and
CJEU case law. This glossary reflects the legal position as of May 2026. Always verify
against current authoritative sources before relying on a definition for compliance.
