FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime
WORKDIR /app
RUN useradd --create-home --shell /bin/bash appuser
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY models ./models
ENV PATH="/app/.venv/bin:$PATH"
ENV MODELS_DIR="/app/models"
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=15s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "cctv_lens_calc.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM builder AS test-builder
RUN uv sync --frozen --all-extras --no-editable

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS test
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=test-builder /app/.venv /app/.venv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY models ./models
COPY tests ./tests
COPY scripts ./scripts
ENV PATH="/app/.venv/bin:$PATH"
ENV MODELS_DIR="/app/models"
RUN playwright install chromium
CMD ["pytest", "-v", "--tb=short"]
