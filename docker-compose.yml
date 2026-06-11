FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для pandas/openpyxl
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p temp

CMD ["python", "-m", "bot.main"]
