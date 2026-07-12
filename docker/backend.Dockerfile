# ── Builder: compilers + pip install into an isolated venv ──────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# The GPU stack (nvidia-*/cuda-*/triton pins) is ~7GB of CUDA libraries that
# are useless in a container without a GPU runtime — Kronos already falls back
# to CPU (kronos_service.py checks torch.cuda.is_available()). Install the
# CPU-only torch wheel from PyTorch's own index and drop the GPU pins.
RUN python -m venv /opt/venv \
    && grep -viE '^(nvidia-|cuda-|triton==|torch==)' requirements.txt > requirements.cpu.txt \
    && /opt/venv/bin/pip install --no-cache-dir \
        torch==2.12.1+cpu --index-url https://download.pytorch.org/whl/cpu \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.cpu.txt

# ── Runtime: slim base + finished venv only (no compilers, no pip cache) ────
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run as an unprivileged user, not root — a container escape from an app
# running as root maps to root on the host in many configurations.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
