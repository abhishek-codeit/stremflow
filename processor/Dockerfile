FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \ 
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN ffmpeg -version | head -1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/processing

CMD ["python" , "worker.py"]