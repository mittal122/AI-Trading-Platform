# ── Builder: compilers + pip install into an isolated venv ──────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Kronos (the AI price forecaster) is optional in Docker: the image ships
# WITHOUT torch by default (KRONOS_ENABLED=false at runtime → /prediction
# returns 503, everything else unaffected). Build with
#   --build-arg INSTALL_KRONOS=true
# to bake in CPU-only torch + the Kronos dependency chain, then run with
# KRONOS_ENABLED=true and the Kronos repo mounted at /kronos.
ARG INSTALL_KRONOS=false

# The GPU stack (nvidia-*/cuda-*/triton pins) is ~7GB of CUDA libraries that
# are useless in a container without a GPU runtime — Kronos already falls back
# to CPU (kronos_service.py checks torch.cuda.is_available()), so even the
# opt-in install uses the CPU-only torch wheel from PyTorch's own index.
RUN python -m venv /opt/venv \
    && grep -viE '^(nvidia-|cuda-|triton==|torch==)' requirements.txt > requirements.cpu.txt \
    && if [ "$INSTALL_KRONOS" = "true" ]; then \
        /opt/venv/bin/pip install --no-cache-dir \
            torch==2.12.1+cpu --index-url https://download.pytorch.org/whl/cpu; \
    else \
        grep -viE '^(sympy|networkx|mpmath|einops|huggingface-hub|hf-xet|safetensors)==' \
            requirements.cpu.txt > requirements.slim.txt \
        && mv requirements.slim.txt requirements.cpu.txt; \
    fi \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.cpu.txt \
    # pip itself is never used at runtime — drop it from the shipped venv
    && /opt/venv/bin/pip uninstall -y pip

# ── Runtime: slim base + finished venv only (no compilers, no pip cache) ────
FROM python:3.12-slim

# Image-scan hardening: apply pending Debian security updates, then drop
# perl-base — this Python-only image never executes perl (verified: zero
# reverse-dependencies in the image), and its unpatched CRITICAL CVEs
# (CVE-2026-42496, CVE-2026-8376) otherwise block deployment at the trivy
# gate. Remove the purge line once Debian ships a fixed perl-base.
RUN apt-get update \
    && apt-get upgrade -y \
    && dpkg --purge --force-depends --force-remove-essential perl-base \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
# numba (pandas_ta's JIT) needs a writable cache location or it hard-crashes
# at import under a read-only root filesystem ("no locator available").
# Point it at /tmp — platforms with readOnlyRootFilesystem mount a writable
# emptyDir there; if even /tmp is read-only, numba degrades to a warning
# instead of crashing because a locator now exists.
ENV NUMBA_CACHE_DIR=/tmp/numba-cache

# Run as an unprivileged user, not root — a container escape from an app
# running as root maps to root on the host in many configurations.
# USER must be the NUMERIC uid (not the name): Kubernetes runAsNonRoot can
# only verify numeric users — a named USER fails admission with
# "cannot verify user is non-root" even though it is.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER 10001:10001

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
