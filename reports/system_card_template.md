# System Card — AI Compliance RAG Assistant

## Intended users
Technical founders, CTOs, AI product managers, and compliance reviewers who need preliminary guidance on EU AI Act / GDPR obligations.

## Intended use
Answer natural-language questions about EU AI Act / GDPR compliance using a curated knowledge base and citations.

## Disallowed use
This system must not be used as final legal advice, to extract personal data/secrets, or for off-topic tasks unrelated to AI compliance.

## Input format
Natural-language question.

## Output format
Structured JSON with answer, citations, confidence, abstained flag, reasoning_trace, and tool_calls.

## Known risks
Incomplete retrieval, outdated source documents, hallucination, prompt injection in retrieved documents, over-reliance on non-primary sources, and latency/cost trade-offs.
