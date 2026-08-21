---
description: Run the approved deep dive for a merged probing plan and add the paper to the dashboard.
on:
  # 병합된 기획서만 딥다이브를 부른다. main 의 push 로 받는 이유는, pull_request
  # 로 받으면 gh-aw 가 PR 브랜치를 체크아웃해 결과를 그 위에 쌓으려다 수집 커밋까지
  # 끌고 와 allowed-files 에 걸리기 때문이다.
  push:
    branches: [main]
    # 수집 PR 은 recommended/ 만, 딥다이브 자신의 결과 PR 은 plan.md 를 건드리지
    # 않으므로 둘 다 걸러진다.
    paths:
      - "analysis/*/plan.md"
  # 실패했을 때 다시 부르는 수단. 조건은 아래 Task 1 이 스스로 확인한다.
  workflow_dispatch:
permissions:
  contents: read
  packages: read
  copilot-requests: write
  issues: read
  pull-requests: read
imports:
  - shared/medical-db.md
safe-outputs:
  create-pull-request:
    title-prefix: "Analysis: "
    labels:
      - "analyzed-${{ github.run_id }}"
    draft: false
    fallback-as-issue: false
    allowed-files:
      - "analysis/**"
    protected-files: allowed
timeout-minutes: 45
---

# Approved deep dive

An approved probing plan landed on `main`. Run the deep dive it describes.

## Task

1. List the directories under `analysis/`. A plan is waiting exactly when
   `analysis/<issue-number>/plan.md` exists and `analysis/<issue-number>/analysis.json`
   does not. Stop with `noop` when no such directory exists. When several do,
   take the highest `<issue-number>`.
2. Read that approved `plan.md`. It is the contract: follow its
   `## Proposed presentation` section for visuals, text sections, and layout
   order. Read the linked issue for any physician comments that refine it, and
   read the paper under `recommended/` again.
3. Use `query-medical-db` to run the analysis the plan describes. Query as many
   times as needed. Report cohort-level aggregates only.
4. Write `analysis/<issue-number>/analysis.json`. This is the dashboard's record
   for this paper, so it has a fixed shape:

   ```json
   {
     "paper": "<paper slug, matching the recommended/ directory name>",
     "verdict": "적용 가능 | 조건부 | 불충분",
     "summary": "무엇을 했나 — 논문이 한 일을 우리 맥락에서 요약",
     "datasets": ["<논문이 쓴 데이터셋>"],
     "dataset_note": "무엇이 필요했나 — 그 데이터가 왜 필요했는지",
     "diffs": [{ "ok": true, "text": "우리에게 있는 것 / 없는 것 한 줄" }],
     "insight": "그래서 무엇이 남나 — 이 논문에서 우리가 실제로 가져갈 수 있는 것",
     "evidence": [{ "label": "규모", "value": "272건/153명" }],
     "figure": "",
     "note": "임상의가 병합 전에 확인해야 할 것",
     "checks": []
   }
   ```

   Rules for the fields:
   - `verdict` is your honest call on whether the method transfers to our cohort.
     `불충분` is a valid and often correct answer; do not inflate it.
   - `diffs` is the heart of the entry. One line per concrete difference, `ok: true`
     when we have what the method needs and `ok: false` when we do not. Include the
     inconvenient ones.
   - `evidence` is the small numbers behind the insight, each one traceable to a query.
   - `figure` stays `""`. When the approved plan calls for a visual, write it as
     `analysis/<issue-number>/figure.svg` instead — a hand-written SVG chart drawn
     from the numbers you queried, with axis labels and units. The dashboard build
     inlines that file. Omit the file rather than drawing a chart you cannot back
     with data.
   - Leave `checks` as an empty array. The verification workflow fills it.
5. Write `analysis/<issue-number>/README.md` for the physician reviewing this pull
   request: the same findings in prose, with the exact query behind every number,
   a clear separation between what the paper reports, what our data shows, and what
   you infer, and a `## Limitations` section.
6. Request one `create-pull-request` safe output. The PR body must summarise
   the findings, list every deviation from the approved plan with a reason, and
   note that an independent verification agent will review it.

   Show the findings, do not only describe them. Result tables, a `mermaid`
   `xychart-beta` or `pie` chart of a distribution, a mermaid diagram of the
   cohort filtering that produced your denominators, collapsed `<details>`
   blocks holding the full query output — GitHub renders all of these in the
   body. Every visual must plot numbers you queried, and `figure.svg` stays the
   one that reaches the dashboard.

## Constraints

- Never widen the scope beyond the approved plan; propose additions in the PR
  body instead of doing them.
- Every claim about the paper needs its source link.
- Do not overstate: a finding on this cohort is hypothesis-generating.
