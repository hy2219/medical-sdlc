FROM postgres:17-alpine

LABEL org.opencontainers.image.source="https://github.com/hy2219/medical-sdlc"

# 빌드에만 필요한 원본(data/hospital.csv, data/images)은 저장소에 포함하지 않습니다.
# 실습은 ghcr.io/hy2219/medical-sdlc-db 를 pull 하며, 이미 DB 에 적재된 상태입니다.
COPY ["data/hospital.csv", "/data/hospital.csv"]
COPY ["data/images", "/data/images"]
COPY ["init.sql", "/docker-entrypoint-initdb.d/01-init.sql"]
COPY ["create-llm-role.sh", "/docker-entrypoint-initdb.d/02-create-llm-role.sh"]
