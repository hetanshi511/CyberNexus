FROM python:3.11-slim

WORKDIR /app

# System deps: tesseract (OCR), libGL (Pillow), glib
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium) and their system dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
