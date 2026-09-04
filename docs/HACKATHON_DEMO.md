# BIS Sahayak: 3-5 Minute Hackathon Demo

## Before presenting

Start the stack from the project root:

```powershell
docker compose up -d --build
```

Open `http://localhost:3000`. The backend API documentation is at `http://localhost:8000/docs`.

Use the examples below only when the Gemini provider is available. They are selected from the documents currently indexed in the local knowledge base.

## Demo flow

1. **Introduce the problem (20 seconds).** Explain that BIS information is distributed across standards and guidance documents, so a user may not know where to find supporting evidence.
2. **Ask BIS and show sources (40 seconds).** In **Ask BIS**, ask: `What does IS 302 Part 1 cover?` Show the answer and its citations. Explain that citations are constructed from retrieved database evidence, not authored by Gemini.
3. **Recommend a standard (40 seconds).** Open **Standards** and enter: `electric pressure cooker`. Show any returned candidate, evidence excerpts, and source citations. Describe it as a candidate, not a legal determination.
4. **Review compliance evidence (35 seconds).** Open **Compliance** and enter: `household electrical appliance`. Explain that requirements are shown only when retrieved evidence supports them, and are not labelled mandatory unless the evidence explicitly says so.
5. **Show public-facing assistance (35 seconds).** In **Hallmarking**, ask: `What should I know about hallmarking gold jewellery?` Or use **Consumer Help** with: `What are the guidelines for complaints about BIS certified products?`
6. **Show multilingual support (25 seconds).** Select Hindi or Bengali and ask an IS 302 question. The language selection changes the response instruction; standards and citations remain retrieved evidence.
7. **Show safe uncertainty (25 seconds).** Ask: `What BIS standard applies to a rocket engine?` Explain that the application reports insufficient evidence rather than inventing a standard. The **Laboratories** screen likewise reports an empty result when no authoritative row exists.
8. **Close with the architecture (20 seconds).** Next.js UI -> FastAPI -> Gemini embedding/retrieval against PostgreSQL + pgvector -> evidence-only generation -> DB-derived citations and validation.

## If Gemini quota or provider access is unavailable

Do not present fabricated answers. Show the running frontend, workflows, API documentation, and user-safe error or insufficient-evidence behavior. Explain that the offline backend test suite covers retrieval, citation construction, malformed/empty-output handling, and the bounded primary/fallback generation path without consuming Gemini quota.

## Presenter notes

- The local knowledge base has 6 documents and 176 chunks; it is intentionally a limited demo corpus.
- Do not call a recommendation a confirmed legal requirement unless the response explicitly says that retrieved evidence establishes it.
- Do not claim laboratory coverage beyond the authoritative rows stored in the database.
