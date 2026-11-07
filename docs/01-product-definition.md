# Móyee — Stage 1: Product Definition (Refinement Draft)

**Status:** Draft for review · **Source:** PRD v0.1 · **Next stage:** MVP Specification

This document sharpens PRD v0.1 sections 1–5. It doesn't restate the PRD. It points out where the definition is too broad to build against and suggests decisions.

---

## 1. Key observations on PRD v0.1

| # | Observation | Why it matters |
|---|---|---|
| O1 | **Three primary personas** (undergrad, postgrad, professional) | Each one needs different features, depth and pricing. If we design for all three, a solo MVP ends up generic. |
| O2 | **The chapter structure (Chapter One–Five, "Summary, Conclusion and Recommendations")** and **Paystack/Flutterwave** point strongly to West African, and especially Nigerian, university research | This is an underserved segment. Global tools (Elicit, SciSpace, Consensus) don't build for it. It's our strongest wedge. |
| O3 | **Positioning describes what Móyee is, not who it beats or why** | We need one sentence that sets us apart from Elicit, SciSpace, NotebookLM, Zotero and ChatGPT. |
| O4 | **The MVP in §15 covers about 9 modules** | That's realistically 9–15 months of work for one developer. It needs a hard cut in Stage 2. |
| O5 | **Final-year project constraints** (deadline, budget, defence requirements) aren't stated | They decide scope, AI provider choice and whether billing is real or "billing-ready". |

---

## 2. Competitive landscape (summary)

| Tool | Strength | Gap Móyee can exploit |
|---|---|---|
| Elicit / Consensus | Paper search and extraction, literature matrices | No writing, no project continuity, USD pricing |
| SciSpace | PDF chat, literature review, writer | Feature sprawl, USD pricing, generic structure |
| NotebookLM | Grounded Q&A over uploaded sources | No academic discovery, citations or thesis structure |
| Zotero / Mendeley | Reference management | No AI understanding or synthesis |
| ChatGPT / Gemini | General reasoning | Makes up citations, no project memory or evidence trail |

**Proposed differentiator:** *the only workspace that takes a student from topic to a defended, properly referenced project, where every AI claim traces back to a source page, priced and structured for the student's own university system.*

---

## 3. Proposed refined definitions

### 3.1 Positioning statement (draft)
> For **final-year undergraduate and postgraduate students** who must produce a structured research project, **Móyee** is an **evidence-grounded research workspace** that connects source discovery, document understanding, literature review and chapter writing in one project. Unlike general AI chatbots, Móyee never presents an uncited claim as fact. Unlike global research tools, it follows the chapter structure and payment realities its users actually work with.

### 3.2 Persona priority (proposed)
1. **Primary (MVP is designed for them):** final-year undergraduate writing a 5-chapter project.
2. **Secondary (supported, not optimised):** Master's students with the same workflow and more sources.
3. **Deferred:** PhD candidates and professional researchers (they need larger libraries, collaboration and advanced analysis).

### 3.3 The core job to be done
> "Help me pick a viable topic, find and understand credible sources, and turn them into a properly referenced Chapter Two, without making things up."

The literature review (Chapter Two) is the sharpest pain point and the clearest place to show off Móyee's grounded AI. The MVP should make this flow excellent before it moves on.

### 3.4 Three differentiators to protect
1. **Evidence traceability.** Every AI claim links to a document, page and passage, or is clearly labelled as AI interpretation.
2. **Project continuity.** Topic, questions, sources, matrix, notes and chapters all live in one project, and the AI remembers them.
3. **Local fit.** Configurable chapter templates, local currency pricing and local payment methods.

---

## 4. Decisions (confirmed)

| Decision | Outcome |
|---|---|
| D1 Personas | **All three equally:** undergrad, postgrad, professional |
| D2 Market | **Global from day one** |
| D3 Timeline | **Under 3 months** |
| D3 Team | **Solo** |
| D3 Budget | **Near zero** (free tiers only) |
| D4 Billing | **Billing-ready:** plans and limits enforced, Paystack in test mode |

Because of D1 and D2, §3.1–3.2 and differentiator #3 change as follows:
- **Positioning:** "For **students and researchers** who need to turn sources into credible written work, Móyee is an evidence-grounded research workspace…" The thesis-specific framing is gone.
- **Persona handling:** all three are served by **one generic project workflow**. Persona differences become *settings* (research level, document template, citation style), not separate features.
- **Differentiator #3** changes from "local fit" to **"Affordable and adaptable":** configurable document templates (5-chapter thesis, journal article, report), with pricing designed so students can afford it.

## 5. Constraint reality check

> [!WARNING]
> Solo developer + under 3 months + zero budget + broad audience is the tightest combination possible. PRD §15 lists about 9 modules for the MVP. In about 12 weeks, one person can realistically ship **4–5 polished modules**.

**What this means for later stages:**
1. **Stage 2 (MVP):** cut hard. The defensible core is **Project → Discover/Upload → Grounded Q&A with page citations → Literature matrix → Basic writing + references → Export.** Methodology assistant, topic development and dataset analysis become *prompt modes inside the assistant*, not separate modules.
2. **Stage 4 (Stack):** prefer managed free tiers over self-run infrastructure, e.g. Supabase (Postgres + pgvector + Auth + Storage), Gemini/Groq free-tier LLMs, OpenAlex (free, no key), Vercel for the frontend. Celery + Redis may not be worth the operational cost at MVP stage.
3. **Global + Paystack:** Paystack test mode is fine for the demo. For a real global launch, revisit Stripe, Lemon Squeezy or Paddle as merchant of record.
4. **Free-tier AI limits** (rate limits and data-use terms on free tiers) must be written into the plan limits and the privacy policy.
