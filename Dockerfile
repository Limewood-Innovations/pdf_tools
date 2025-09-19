# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY pdf_batch_tools.py ./

VOLUME ["/01_input", "/02_processed", "/03_cleaned", "/99_archived"]

ENTRYPOINT ["python", "/app/pdf_batch_tools.py"]
