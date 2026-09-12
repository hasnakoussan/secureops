# Dockerfile du Notification Service.
# Build depuis la RACINE du projet : docker build -f services/notification/Dockerfile .

FROM python:3.12-slim

WORKDIR /app/services/notification

COPY services/notification/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/notification/ .

CMD ["python", "app.py"]
