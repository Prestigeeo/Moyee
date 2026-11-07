# 05 — Móyee Evaluation Benchmark & Live Testing Guide

This document provides both the **automated quantitative evaluation suite** and a **step-by-step live testing script** to evaluate every module of **Móyee** end-to-end.

---

## 1. Automated Quantitative AI & RAG Evaluation Script

The quantitative benchmark script is located at:
- [`apps/api/scripts/evaluate_rag.py`](../apps/api/scripts/evaluate_rag.py)

### How to Run It
From your terminal:
```bash
cd apps/api
.venv/bin/python scripts/evaluate_rag.py
```

### What It Evaluates
| Metric | Target | Description |
|---|---|---|
| **Citation Precision & Hallucination Stripping** | `100%` | Verifies that any unverified marker (`[S99]`, `[S4]`) is stripped immediately while valid markers (`[S2]`, `[S1]`) are renumbered sequentially (`[1]`, `[2]`) and bound to exact page numbers. |
| **Adversarial Prompt-Injection Neutralisation** | `100%` | Verifies that embedded prompt-injection directives inside PDF chunks (`Ignore all previous instructions...`, `Disregard prior directives...`, `system prompt`) are redacted before reaching the LLM. |
| **Hybrid Subword / Semantic Discrimination** | `100%` | Verifies that morphological/subword 4-gram cosine similarity + lexical RRF retrieves semantically related academic passages (`adaptation` ↔ `adapting`) while rejecting unrelated topics (`0%` false-positive rate). |
| **AI Project Advisor Completeness & Routing** | `100%` | Verifies that `generate_project_recommendations` and `requests_project_guidance` generate complete project descriptions, 4 research questions, 4 objectives, and 6+ discovery search keywords. |

### Full Automated Test Suite (30 Integration & Unit Tests)
To run all 30 automated API, database isolation, citation formatting, and AI gateway tests:
```bash
cd apps/api
.venv/bin/pytest -v
```

---

## 2. Step-by-Step Live UI Testing Script (5-Minute Walkthrough)

Use these exact steps and sample inputs to test the live application at `http://localhost:3000` (or your Vercel URL):

### Test 1: AI Project Setup & Topic Recommendations
1. Go to **New Project** (`/app/projects/new`).
2. Enter:
   - **Project title:** `AI Feedback & Academic Writing`
   - **Research topic:** `Impact of evidence-grounded AI feedback on undergraduate academic writing and revision quality`
   - **Academic discipline:** `Educational Technology`
3. Click **✦ Generate Description & Questions with AI**.
4. **Expected Result:**
   - The **Project description**, **4 Research questions**, **4 Research objectives**, **Discovery search keywords**, and **AI Recommended Methodology & Design** banner are automatically populated.
5. Click **Create project**.
6. On the **Project Overview** page, test clicking **Generate AI recommendations** → **Apply all to project**, or click any **Suggested Discovery Search Query** pill to jump straight into OpenAlex search.

---

### Test 2: OpenAlex Discovery + Full-Text PDF Ingestion
1. Inside **Academic Discovery** (`/app/p/[projectId]/discover`), check **Open access only** and search:
   ```text
   automated writing evaluation feedback revision undergraduate
   ```
2. On 2–3 Open-Access papers, click **Save + Fetch Full PDF**.
3. **Expected Result:**
   - If the publisher allows direct PDF download, the badge updates to **`Full-text PDF indexed (N pages)`** and shows **Open in Reader →**.
   - If a publisher blocks automated downloads (only providing an HTML landing page), Móyee gracefully saves the metadata + abstract and shows a **Fetch Full-Text PDF** bar inside the Document Reader where you can paste a direct PDF link or upload the PDF file.

---

### Test 3: Document Reader & Grounded 5-Part Summary
1. Click **Open in Reader →** on any saved paper (or open it from **Project Library**).
2. Click **Extract summary** on the right panel.
3. **Expected Result:**
   - Móyee extracts **Research Aim**, **Methodology & Design**, **Population & Sample**, **Key Findings**, and **Stated Limitations**, each with a clickable **`[p. X]`** badge.
   - Clicking **`[p. X]`** jumps the left-hand reader directly to that page and highlights the exact supporting quote in yellow.

---

### Test 4: Cross-Paper Synthesis & Citation Verification in Assistant
1. Open **Research Assistant** (`/app/p/[projectId]/assistant`).
2. Test these 3 prompts across your saved papers:
   - **Cross-Paper Trend Prompt:**
     ```text
     Is there any common trend in these papers, and where do their findings agree or differ?
     ```
   - **Research Question Formulation Prompt:**
     ```text
     Based on my research topic and saved sources, generate potential research questions and objectives.
     ```
   - **Methodology Advisor Prompt (switch mode to Methodology):**
     ```text
     What research design, sampling strategy, and data analysis method would you recommend for my topic?
     ```
3. **Expected Result:**
   - The Assistant synthesises across multiple sources using **Gemini 3 Flash / Groq 120B** (not "Limited mode"), attaches numbered inline citation badges (`[1]`, `[2]`), separates **Grounded Answer** from **Interpretation & Guidance** and **Evidence Limitations**, and lets you click any citation card to verify the exact quote in the Reader.

---

### Test 5: Literature Matrix & Synthesis Studio
1. Open **Literature Matrix** (`/app/p/[projectId]/literature`).
2. Select 2–5 sources, name the matrix `Core Literature Comparison`, and click **Generate matrix**.
3. **Expected Result:**
   - Produces an 8-column comparison table (`Aim`, `Methodology`, `Sample`, `Data Collection`, `Analysis`, `Findings`, `Limitations`, `Relevance`) with page references, plus **Cross-Study Synthesis Notes** (Recurring Themes, Methodological Comparison, and Potential Research Gaps).
   - Click any cell to edit inline, or click **Export CSV** to download the spreadsheet.

---

### Test 6: Writing Studio & Word (`.docx`) Export
1. Open **Writing Studio** (`/app/p/[projectId]/write`).
2. Create a document (initialized with your project’s 5-chapter Thesis template).
3. Write a paragraph in **Chapter One: Introduction**, click **Insert citation** in the right sidebar to insert formatted APA 7th / IEEE / Harvard inline citations, and test an AI writing action (**Academic tone** or **Improve clarity**).
4. Click **Export Word (.docx)** to download the formatted Word manuscript with auto-generated References at the end.
