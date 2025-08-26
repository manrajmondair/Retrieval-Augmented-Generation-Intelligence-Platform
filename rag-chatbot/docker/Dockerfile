# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libmagic1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS runtime
RUN useradd -m -u 10001 appuser
RUN python -m venv /opt/venv && . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install \
      fastapi==0.115.0 \
      uvicorn==0.30.6 \
      gunicorn==22.0.0 \
      pydantic-settings==2.4.0 \
      python-dotenv==1.0.1 \
      loguru==0.7.2 \
      prometheus-fastapi-instrumentator==7.0.0 \
      opentelemetry-sdk==1.27.0 \
      opentelemetry-instrumentation-fastapi==0.48b0 \
      redis==5.0.8 \
      langchain==0.2.16 \
      langchain-openai==0.1.23 \
      langchain-community==0.2.16 \
      qdrant-client==1.11.3 \
      chromadb==0.5.5 \
      pinecone-client==5.0.1 \
      rank-bm25==0.2.2 \
      pypdf==5.0.1 \
      unstructured==0.15.7 \
      markdown==3.6 \
      python-multipart==0.0.9 \
      sse-starlette==2.1.3

ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY app /app/app
COPY data /app/data
COPY web /app/web

EXPOSE 8000
USER 10001

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", ":8000", "app.main:app"]

