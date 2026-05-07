FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UNMET_DEMAND_DB_PATH=/app/data/unmet_demand.db \
    UNMET_DEMAND_SERVICE_MODE=dashboard

WORKDIR /app

COPY pyproject.toml README.md ./
COPY data ./data
COPY scripts ./scripts
COPY src ./src

RUN pip install --no-cache-dir -e .

EXPOSE 8501

CMD ["python", "scripts/service_entrypoint.py"]
