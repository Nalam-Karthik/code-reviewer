FROM python:3.11-slim

WORKDIR /app


RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    curl \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV PYTHONPATH=/app

CMD ["python", "app/run.py"]
