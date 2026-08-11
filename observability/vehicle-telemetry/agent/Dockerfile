FROM python:3.12-slim

RUN groupadd -r triage && useradd -r -g triage -u 10003 triage

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY triage_agent.py .

USER triage
EXPOSE 9099

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
                 sys.exit(0 if urllib.request.urlopen('http://localhost:9099/healthz',timeout=3).status==200 else 1)"

ENTRYPOINT ["python", "-u", "triage_agent.py"]
