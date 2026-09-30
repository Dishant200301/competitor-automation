FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium
COPY backend/ .
RUN useradd --create-home researcher && mkdir -p /workspace/backend/data && chown -R researcher:researcher /workspace
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# Install browsers into a shared directory accessible by the unprivileged worker.
RUN python -m playwright install chromium && chmod -R a+rX /ms-playwright
USER researcher
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
