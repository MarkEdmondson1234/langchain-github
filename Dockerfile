FROM python:3.9-slim

WORKDIR /app

# Install required packages for building hnswlib
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential poppler-utils tesseract-ocr-all libmagic1 \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
