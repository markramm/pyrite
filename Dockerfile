
FROM python:3.11-slim

WORKDIR /app

# System deps for watchdog/inotify
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8088
CMD ["python", "-m", "cascade_research.server.api"]
