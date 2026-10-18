# syntax=docker/dockerfile:1

# ---- builder: install dependencies into a virtualenv ----
FROM python:3.14-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- runtime: slim image, non-root user ----
FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod
RUN useradd --create-home --uid 1000 app
WORKDIR /app
RUN mkdir staticfiles && chown app:app staticfiles
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . .
USER app
# Collect the admin's static files into the image. The key is a throwaway value that only lets
# the production settings load; it is not stored in the image's environment.
RUN DJANGO_SECRET_KEY=build-time-only python manage.py collectstatic --noinput
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/').status == 200 else 1)"
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
