FROM python:3.12-slim

RUN groupadd -r mock && useradd -r -g mock -u 10002 mock

WORKDIR /app
COPY mock_pandora.py .

USER mock
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; \
                 sys.exit(0 if urllib.request.urlopen('http://localhost:8080/healthz',timeout=3).status==200 else 1)"

ENTRYPOINT ["python", "-u", "mock_pandora.py"]
