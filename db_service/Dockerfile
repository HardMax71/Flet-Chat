FROM python:3.11-slim

RUN apt-get update && apt-get install -y postgresql-client

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

CMD ["sh", "-c", "until pg_isready -h db -p 5432; do echo 'Waiting for database...'; sleep 2; done; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]