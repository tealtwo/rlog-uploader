FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    openssh-client \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY rlog_downloader.py .
COPY extract_web_server_rlogs.py .

RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh && \
    mkdir -p /app/data

EXPOSE 3445

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:3445/', timeout=5)" || exit 1

CMD ["python", "extract_web_server_rlogs.py"]
