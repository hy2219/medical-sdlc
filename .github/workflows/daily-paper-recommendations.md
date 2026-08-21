---
description: Find new papers from the tracked journals and conferences that are relevant to the masked medical dataset, and record them daily.
on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:
    inputs:
      date:
        description: Publication date in YYYY-MM-DD; defaults to yesterday in Asia/Seoul.
        required: false
        type: string
env:
  REQUESTED_DATE: ${{ inputs.date }}
permissions:
  contents: read
  packages: read
  copilot-requests: write
imports:
  - shared/medical-db.md
mcp-scripts:
  search-papers:
    description: Search ten clinical and imaging journals plus five method conferences at once for a Copilot-authored query in a publication-date range.
    inputs:
      query:
        description: Search query authored after examining the masked dataset.
        required: true
      startDate:
        description: First publication date in YYYY-MM-DD.
        required: true
      endDate:
        description: Last publication date in YYYY-MM-DD.
        required: true
    run: |
      python3 "$GITHUB_WORKSPACE/tools/search_papers.py" "$INPUT_QUERY" "$INPUT_STARTDATE" "$INPUT_ENDDATE"
safe-outputs:
  create-pull-request:
    title-prefix: "Daily paper recommendations: "
    labels:
      - collected
    draft: false
    fallback-as-issue: false
    allowed-files:
      - "recommended/**"
    protected-files: allowed
    max-patch-files: 500
    max-patch-size: 4096
timeout-minutes: 30
---

# Daily paper recommendations

## Task

1. Determine the research date:
   - Use `REQUESTED_DATE` when it is a valid `YYYY-MM-DD` value.
   - Otherwise use yesterday's date in `Asia/Seoul`, because the current day's publication metadata may be incomplete.
2. Use `query-medical-db` several times to understand the masked dataset: columns, cohort size, diagnoses, demographics, and imaging characteristics.
3. Based on the observed dataset, author a broad search query yourself. Do not reuse a fixed query from the repository. Keep it to a few words, because it is matched against titles and abstracts.
4. Call `search-papers` first with the research date as both `startDate` and `endDate`. It searches Nature, Nature Medicine, Nature Communications, Nature Biomedical Engineering, npj Digital Medicine, The Lancet Digital Health, Radiology, Radiology: Artificial Intelligence, European Radiology and Medical Image Analysis through OpenAlex, and MICCAI, IPMI, CVPR, NeurIPS and ICLR through arXiv, then returns one deduplicated list newest first.
5. Read every returned article, exclude duplicates already present under `recommended/`, and use clinical and methodological judgment to retain only papers plausibly supported by or useful for this dataset. Prefer work a clinician could act on: papers reporting on patient cohorts, external validation, or reader studies outrank a purely methodological advance with no clinical readout, however strong the method.
6. The target is at least 3 retained papers. If fewer than 3 qualify, repeat the search with progressively wider windows ending on the research date: 7 days, then 30 days. Stop as soon as at least 3 papers qualify. Never lower the relevance standard merely to reach 3.
7. Pick two to four short **axes** naming the recurring themes across the retained
   papers, in Korean. An axis is what the physician would compare papers on, such as
   `기관 간 일반화` or `라벨 잡음`. Tag every paper with the axes it belongs to.
8. For every retained paper, write `recommended/YYYY-MM-DD/<paper-slug>/paper.json`:

   ```json
   {
     "id": "<paper-slug, same as the directory name>",
     "title": "<title>",
     "authors": ["<author>"],
     "venue": "<venue field as returned by search-papers>",
     "year": 2026,
     "source": "<source field as returned by search-papers>",
     "url": "https://doi.org/<doi>",
     "abstract": "<abstract as published, plain text, no markup>",
     "axes": ["<axis>"],
     "takeaway": "<한 문장. 이 논문이 주장하는 결과.>",
     "relevance": "<두세 문장. 우리 코호트의 무엇이 이 논문과 맞물리는지, 실제로 관찰한 수치를 근거로.>",
     "caveat": "<한두 문장. 이 논문이 우리 데이터로는 확인해 줄 수 없는 것.>",
     "check": "<한 문장. 딥다이브에서 확인해 볼 만한 구체적인 질문.>"
   }
   ```

   `takeaway`, `relevance`, `caveat`, `check` 는 모두 한국어로, 임상의가 읽는
   문장으로 씁니다. `relevance` 는 코호트 수준 수치만 인용하고 환자 단위 값은
   쓰지 않습니다. 근거가 없으면 지어내지 말고 빈 문자열로 둡니다.

   Leave `abstract` as an empty string when the source publishes none — never
   write a summary of your own into it, because later stages quote this field as
   the paper's own words.
9. Write `recommended/YYYY-MM-DD/README.md` for the physician reviewing the pull request:
   - the research date, actual search window, and exact search query;
   - a cohort-level description without patient-level values;
   - one section per retained paper explaining why it is relevant, what in our data
     supports it, and what it cannot tell us;
   - source links and a clear note that recommendations require physician review.
10. Request one `create-pull-request` safe output containing only `recommended/**` changes. Explain the selection in the PR body.
11. If no new relevant papers remain after the 30-day window, call `noop` with a short explanation instead of creating files.
