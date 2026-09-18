# Dockerfile du Response Service.
# Build depuis la RACINE du projet : docker build -f services/response/Dockerfile .

FROM python:3.12-slim

WORKDIR /app/services/response

COPY services/response/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/response/ .

CMD ["python", "-u", "app.py"]
