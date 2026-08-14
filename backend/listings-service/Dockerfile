FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LISTINGS_DB_PATH=/data/listings.db
ENV LOCAL_UPLOAD_DIR=/data/uploads
VOLUME ["/data"]

EXPOSE 5002

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "2", "app:app"]
