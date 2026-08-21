---
description: Probe one recommended paper against the masked dataset and propose an analysis plan for physician approval.
on:
  issues:
    types: [opened]
permissions:
  contents: read
  packages: read
  copilot-requests: write
  issues: read
imports:
  - shared/medical-db.md
safe-outputs:
  create-pull-request:
    title-prefix: "Probing: "
    labels:
      - "probing-${{ github.event.issue.number }}"
    draft: false
    fallback-as-issue: false
    allowed-files:
      - "analysis/**"
    protected-files: allowed
  add-comment:
timeout-minutes: 30
---

# Paper probing

An issue requesting analysis of one recommended paper has just been opened.

## Task

1. Read the issue title and body. Extract the paper path under
   `recommended/` and the physician's focus. If the issue is not a paper
   analysis request, or names no readable paper file, call `noop` with a short
   explanation and stop.
2. Read that `paper.json` and the `README.md` of its date directory.
3. Use `query-medical-db` several times to characterise the cohort for this
   specific question: size, label distribution, demographics, imaging
   characteristics, and the size of any subgroup the physician named.
4. Keep this **light**. Propose an analysis; do not run it, do not produce
   final findings, do not build the dashboard entry.
5. Write `analysis/<issue-number>/plan.md`. This is the only file you commit and
   it holds the plan alone, because merging the pull request is what approves it:

   - `# Plan: <paper title>` — issue link, paper path, DOI, physician focus.
   - `## Proposed presentation` — the dashboard entry to build. Which visuals
     (chart type, axes, what each encodes and why that encoding suits this
     question), which text sections, and the layout order. Justify each choice
     against the physician's focus rather than listing generic charts.
   - `## Open questions` — what the physician must decide before the deep dive.

6. Request one `create-pull-request` safe output containing only that file. The
   **pull request body carries the full probing report**, with these sections:

   - `## Abstract` — the paper's abstract, quoted with its source link.
   - `## Paper dataset` — the cohort the paper used: source, size, labels,
     modality, splits, and how outcomes were defined. Say so explicitly when
     the paper does not report something.
   - `## Our dataset` — cohort-level description from `llm.hospital` only.
   - `## Differences` — a table comparing the two datasets row by row
     (size, modality, labels, demographics, annotation, outcome definition),
     with a plain-language note on what each difference means for
     transferability.
   - `## Relevance and insight` — why this paper is relevant to our data given
     the physician's focus, and what specific, defensible insight a deep dive
     could produce. Name what we cannot conclude, too.
   - a closing line stating that merging approves the committed plan.

   Use visuals in the body wherever they carry the point faster than a
   paragraph: comparison tables, a `mermaid` diagram of the proposed analysis
   flow, a mermaid `xychart-beta` or `pie` chart of a distribution you already
   queried, task lists, collapsed `<details>` blocks for long query output.
   GitHub renders all of these. Every chart must plot numbers you actually
   queried, never illustrative ones.

7. Add one comment on the issue linking the pull request and asking the
   physician to review the proposed presentation.

## Constraints

- Every factual claim about the paper needs its source link.
- Distinguish clearly between what the paper reports, what our data shows, and
  what you are inferring.
- Recommendations require physician review before any clinical use.
