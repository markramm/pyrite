# =============================================================================
# Stage 1: Build SvelteKit frontend
# =============================================================================
FROM node:22-alpine AS frontend

WORKDIR /build/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

# =============================================================================
# Stage 2: Python application
# =============================================================================
FROM python:3.12-slim AS runtime

ARG INSTALL_SEMANTIC=true

WORKDIR /app

# System deps for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install pyrite with server + ai extras
COPY pyproject.toml README.md ./
COPY pyrite/ pyrite/
COPY extensions/ extensions/

RUN pip install --no-cache-dir ".[server,ai,cli]" && \
    if [ "$INSTALL_SEMANTIC" = "true" ]; then \
        pip install --no-cache-dir ".[semantic]"; \
    fi

# Remove build deps to slim the image
RUN apt-get purge -y build-essential gcc && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy built frontend from stage 1
COPY --from=frontend /build/web/dist/ /app/web/dist/

# Copy deploy scripts (for seeding etc.)
COPY deploy/ /app/deploy/

# Create non-root user
RUN useradd --create-home --shell /bin/bash pyrite

# Data directory for volumes
ENV PYRITE_DATA_DIR=/data
ENV PYRITE_STATIC_DIR=/app/web/dist
RUN mkdir -p /data && chown pyrite:pyrite /data
VOLUME /data

USER pyrite

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8088/health')" || exit 1

CMD ["pyrite-server"]
