# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /src/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build && npm run build:ssr

FROM node:22-bookworm-slim AS runtime

ARG LITESTREAM_VERSION=0.5.16

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/qport-venv
ENV PATH="/opt/qport-venv/bin:${PATH}"

WORKDIR /app
COPY python/requirements.txt /app/python/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/python/requirements.txt boto3

RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) litestream_arch="x86_64" ;; \
      arm64) litestream_arch="arm64" ;; \
      *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-${litestream_arch}.tar.gz" \
      | tar -xz -C /usr/local/bin litestream; \
    litestream version

COPY python/ /app/python/
COPY frontend/ssr/ /app/frontend/ssr/
COPY --from=frontend-build /src/frontend/dist/ /app/frontend/dist/
COPY --from=frontend-build /src/frontend/dist-ssr/ /app/frontend/dist-ssr/
COPY deploy/ /app/deploy/

RUN chmod +x /app/deploy/start-render.sh \
    && mkdir -p /data/qport /tmp/litestream-meta

ENV QPORT_AUTH_NAMESPACE=/data/qport
ENV PORT=10000

EXPOSE 10000

CMD ["/app/deploy/start-render.sh"]
