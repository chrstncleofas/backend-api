# =============================================================================
# Stage 1 — builder: install dependencies into an isolated venv
# =============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2 — runtime: lean image with only what is needed to run
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Copy installed packages from builder — no pip or build tools in final image
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Run as non-root user (OWASP best practice)
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
