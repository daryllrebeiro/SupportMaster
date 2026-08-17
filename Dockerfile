FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SUPPORTMASTER_RUN_DB=/app/.supportmaster/runs.db SUPPORTMASTER_SESSION_DB=/app/.supportmaster/sessions.db SUPPORTMASTER_AUTH_MODE=OPTIONAL
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY supportmaster ./supportmaster
COPY fixtures ./fixtures
COPY README.md .
RUN mkdir -p /app/.supportmaster
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health/live')"
CMD ["python", "-m", "supportmaster.web", "--host", "0.0.0.0", "--port", "8001"]
