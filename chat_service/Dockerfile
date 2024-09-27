FROM python:3.11-slim

RUN apt-get update && apt-get install -y postgresql-client telnet redis-tools

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]