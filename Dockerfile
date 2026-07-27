FROM python:3.12-slim AS runtime

ARG MONGO_TOOLS_VERSION=100.15.0
ARG MONGOSH_VERSION=2.9.2

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBBACKUP_UI_HOST=0.0.0.0 \
    DBBACKUP_UI_PORT=7575

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl default-mysql-client postgresql-client \
    && curl --fail --location --silent --show-error --output /tmp/mongodb-tools.deb \
        "https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-${MONGO_TOOLS_VERSION}.deb" \
    && curl --fail --location --silent --show-error --output /tmp/mongosh.deb \
        "https://downloads.mongodb.com/compass/mongodb-mongosh_${MONGOSH_VERSION}_amd64.deb" \
    && apt-get install --no-install-recommends -y /tmp/mongodb-tools.deb /tmp/mongosh.deb \
    && rm --force /tmp/mongodb-tools.deb /tmp/mongosh.deb \
    && apt-get clean \
    && rm --recursive --force /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 appuser \
    && mkdir --parents /data/backups \
    && chown --recursive appuser:appuser /app /data

USER appuser

EXPOSE 7575

VOLUME ["/data/backups"]

CMD ["dbbackup", "serve", "--host", "0.0.0.0", "--port", "7575"]
