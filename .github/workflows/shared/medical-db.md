---
permissions:
  contents: read
  packages: read
  copilot-requests: write
network:
  allowed:
    - defaults
    - api.openalex.org
    - export.arxiv.org
    - doi.org
tools:
  cli-proxy: true
services:
  postgres:
    # 이미지가 public 이라 자격증명 없이 익명으로 받는다. 참가자 계정으로 로그인하면
    # 복제된 저장소에서 패키지 접근이 거부되어 오히려 실패한다.
    image: ghcr.io/hy2219/medical-sdlc-db:latest
    env:
      POSTGRES_DB: medical
      POSTGRES_USER: medical
      POSTGRES_PASSWORD: medical
      LLM_DB_PASSWORD: ${{ secrets.LLM_DB_PASSWORD }}
    ports:
      - 5432:5432
    options: >-
      --health-cmd "pg_isready -U medical -d medical"
      --health-interval 5s
      --health-timeout 5s
      --health-retries 30
steps:
  - name: Install PostgreSQL client
    run: sudo apt-get update -qq && sudo apt-get install -y -qq postgresql-client
mcp-scripts:
  query-medical-db:
    description: Run one read-only SELECT or WITH query against the masked llm.hospital view.
    inputs:
      sql:
        description: Read-only SQL using the llm.hospital view.
        required: true
    run: |
      case "$INPUT_SQL" in
        [Ss][Ee][Ll][Ee][Cc][Tt]*|[Ww][Ii][Tt][Hh]*) ;;
        *) printf 'Only SELECT or WITH queries are allowed.\n' >&2; exit 2 ;;
      esac
      psql -X -qAt -v ON_ERROR_STOP=1 \
        -h 127.0.0.1 -U llm_reader -d medical \
        --command "$INPUT_SQL"
    env:
      PGPASSWORD: ${{ secrets.LLM_DB_PASSWORD }}
---

## Masked patient dataset

The `llm_reader` role can read only the `llm.hospital` view. Patient names and
national identifiers are already masked there; every other private column is
denied by role permissions.

Rules that always apply:

- Query only `llm.hospital`, using `query-medical-db`.
- Never write patient rows, masked identifiers, free-text records, or images
  into repository files. Report cohort-level aggregates only.
