FROM python:3.12-slim AS base

# Non-root user for safety
RUN groupadd -r pandora && useradd -r -g pandora -u 10001 pandora

WORKDIR /app

# Install deps first to leverage Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pandora_exporter.py .

USER pandora

EXPOSE 9180

# Healthcheck: exporter is alive if /metrics responds
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; \
                 sys.exit(0 if urllib.request.urlopen('http://localhost:9180/metrics',timeout=3).status==200 else 1)"

ENTRYPOINT ["python", "-u", "pandora_exporter.py"]
